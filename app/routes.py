from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app as app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import zipfile
from io import BytesIO
from .models import FileLog, Transaction
from . import db
from config import s3
import os
from dotenv import load_dotenv
import requests
import uuid
import boto3

load_dotenv()

main = Blueprint('main', __name__)

BUCKET_NAME = 'l769ab'
ALLOWED_EXTENSIONS = {'zip', 'rar', 'RAR', 'ZIP'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/')
@login_required
def index():
    files_in_process = FileLog.query.filter_by(user_id=current_user.id).order_by(FileLog.upload_date.desc()).all()
    return render_template('index.html', files_in_process=files_in_process, credits=current_user.credits)

@main.route('/finance', methods=['GET', 'POST'])
@login_required
def finance():
    if request.method == 'POST':
        amount = request.form.get('amount')
        user = current_user

        # Certifique-se de que o valor está correto antes de enviar à API
        if not amount.isdigit():
            return jsonify({'error': 'Valor inválido. Insira um número inteiro.'}), 400

        api_key = os.getenv('OPENPIX_API_KEY')
        headers = {
            'Authorization': f'{api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            "name": f"Recarga para {user.username}",
            "correlationID": str(uuid.uuid4()),
            "value": int(amount),  # Valor em centavos já foi calculado no frontend
            "comment": "Recarga de créditos"
        }

        try:
            response = requests.post('https://api.openpix.com.br/api/v1/qrcode-static', json=payload, headers=headers)
            response.raise_for_status()

            charge = response.json()
            if 'pixQrCode' in charge:
                qr_code = charge['pixQrCode']['qrCodeImage']
            else:
                app.logger.error("Campo 'pixQrCode' não encontrado na resposta")
                return jsonify({'error': 'Erro ao gerar cobrança. Verifique a resposta da API.'}), 500

            # Registrar transação pendente
            new_transaction = Transaction(
                user_id=user.id,
                amount=int(amount),
                description="Recarga via PIX",
                timestamp=db.func.now(),
                status='Pendente',
                correlation_id=payload['correlationID']
            )
            db.session.add(new_transaction)
            db.session.commit()

            return jsonify({'qr_code': qr_code})

        except requests.exceptions.HTTPError as http_err:
            app.logger.error(f"HTTP error occurred: {http_err}")
            return jsonify({'error': 'Erro ao gerar cobrança. Verifique a API Key e os parâmetros.'}), 500
        except Exception as err:
            app.logger.error(f"Other error occurred: {err}")
            return jsonify({'error': 'Erro ao gerar cobrança. Verifique a API Key e os parâmetros.'}), 500

    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('finance.html', transactions=transactions)

@main.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo foi enviado.'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo foi selecionado.'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        try:
            with zipfile.ZipFile(BytesIO(file.read()), 'r') as zip_ref:
                num_folders = sum(1 for z in zip_ref.namelist() if z.endswith('/'))
            cost = num_folders * 1.00

            user = current_user

            if user.credits >= cost:
                user.credits -= cost
                db.session.commit()

                file.seek(0)
                s3_key = f"{current_user.id}/{filename}"
                s3.upload_fileobj(
                    file,
                    BUCKET_NAME,
                    s3_key,
                    ExtraArgs={"ContentType": file.content_type}
                )

                new_log = FileLog(user_id=current_user.id, filename=filename, s3_key=s3_key,
                                  status='Em Processamento', cost=cost)
                db.session.add(new_log)
                db.session.commit()

                return jsonify(
                    {'success': True, 'message': 'Processamento autorizado e iniciado.', 'file_id': new_log.id})
            else:
                new_log = FileLog(user_id=current_user.id, filename=filename, s3_key='',
                                  status='Aguardando Pagamento', cost=cost)
                db.session.add(new_log)
                db.session.commit()

                return jsonify({'success': False, 'message': 'Saldo insuficiente. Por favor, gere um PIX para continuar.', 'file_id': new_log.id, 'custo': cost})

        except Exception as e:
            app.logger.error(f'Ocorreu um erro ao fazer o upload: {str(e)}')
            return jsonify({'error': f'Ocorreu um erro ao fazer o upload: {str(e)}'}), 500

    return jsonify({'error': 'Tipo de arquivo não permitido.'}), 400

@main.route('/process_authorization', methods=['POST'])
@login_required
def process_authorization():
    file_id = request.form.get('file_id')
    file_log = FileLog.query.get(file_id)
    if file_log:
        user = current_user
        if user.credits >= file_log.cost:
            user.credits -= file_log.cost
            file_log.status = 'Em Processamento'
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Saldo insuficiente'}), 400
    return jsonify({'success': False, 'message': 'Arquivo não encontrado'}), 404

@main.route('/cancel_process', methods=['POST'])
@login_required
def cancel_process():
    file_id = request.form['file_id']
    file_log = FileLog.query.get(file_id)
    file_log.status = 'Cancelado'
    db.session.commit()
    flash('Processo cancelado.', 'warning')

    return redirect(url_for('main.index'))

@main.route('/generate_pix/<int:file_id>', methods=['POST'])
@login_required
def generate_pix(file_id):
    file_log = FileLog.query.get(file_id)
    if not file_log or file_log.status != 'Aguardando Pagamento':
        return jsonify({'error': 'Arquivo não encontrado ou pagamento não necessário.'}), 400

    api_key = os.getenv('OPENPIX_API_KEY')
    headers = {
        'Authorization': f'{api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "name": f"Pagamento para {current_user.username}",
        "correlationID": str(uuid.uuid4()),
        "value": int(file_log.cost * 100),  # Valor em centavos
        "comment": f"Pagamento do arquivo {file_log.filename}"
    }

    try:
        response = requests.post('https://api.openpix.com.br/api/v1/qrcode-static', json=payload, headers=headers)
        response.raise_for_status()

        charge = response.json()
        if 'pixQrCode' in charge:
            qr_code = charge['pixQrCode']['qrCodeImage']
            return jsonify({'qr_code': qr_code})
        else:
            return jsonify({'error': 'Erro ao gerar cobrança. Verifique a resposta da API.'}), 500

    except requests.exceptions.HTTPError as http_err:
        return jsonify({'error': f'HTTP error occurred: {http_err}'}), 500
    except Exception as err:
        return jsonify({'error': f'Other error occurred: {err}'}), 500

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@main.route('/register_webhook', methods=['POST'])
@login_required
def register_webhook():
    endpoint_url = os.getenv('WEBHOOK_URL')
    api_key = os.getenv('OPENPIX_API_KEY')
    headers = {
        'Authorization': f'{api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "name": "Webhook de Teste",
        "url": endpoint_url,
        "event": ["PIX_RECEIVED"]
    }

    try:
        response = requests.post('https://api.openpix.com.br/api/v1/webhook', json=payload, headers=headers)
        response.raise_for_status()
        webhook_info = response.json()
        return jsonify({'message': 'Webhook registrado com sucesso!', 'webhook_info': webhook_info})

    except requests.exceptions.HTTPError as http_err:
        return jsonify({'error': f'HTTP error occurred: {http_err}'}), 500
    except Exception as err:
        return jsonify({'error': f'Other error occurred: {err}'}), 500

@main.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    correlation_id = data.get("pixQrCode", {}).get("correlationID")
    if correlation_id:
        transaction = Transaction.query.filter_by(correlation_id=correlation_id).first()
        if transaction:
            transaction.status = 'Concluído'
            db.session.commit()

    return jsonify({'status': 'success'}), 200
