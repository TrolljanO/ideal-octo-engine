from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app as app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import zipfile
from io import BytesIO
from .models import File, Transaction
from . import db
from config import s3
import os
from dotenv import load_dotenv
import requests
import uuid
import http.client
import json

load_dotenv()

main = Blueprint('main', __name__)

BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'zip,rar').split(','))
instance_id = os.getenv('EC2_INSTANCE_ID')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_processing_server_status():
    try:
        response = requests.get(os.getenv('PROCESSING_SERVER_STATUS_URL'))
        if response.status_code == 200 and response.json().get("status") == "active":
            return True
        else:
            return False
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erro ao verificar status do servidor: {e}")
        return False


def start_processing_server(instance_id):
    try:
        ec2_client = boto3.client('ec2', region_name=os.getenv('AWS_REGION'))
        response = ec2_client.start_instances(InstanceIds=[instance_id])
        app.logger.info(f"Iniciando a instância: {instance_id}")
        return True
    except Exception as e:
        app.logger.error(f"Erro ao iniciar o servidor de processamento: {e}")
        return False


@main.route('/')
@login_required
def index():
    files_in_process = File.query.filter_by(user_id=current_user.id).order_by(File.upload_date.desc()).all()
    return render_template('index.html', files_in_process=files_in_process, credits=current_user.credits)


@main.route('/finance', methods=['GET', 'POST'])
@login_required
def finance():
    if request.method == 'POST':
        amount = request.form.get('amount')
        user = current_user

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
            "value": int(amount),
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
            cost = num_folders * 100  # Multiplicado por 100 para converter para centavos

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

                new_file = File(user_id=current_user.id, filename=filename, s3_key=s3_key,
                                status='Em Processamento', cost=cost)
                db.session.add(new_file)
                db.session.commit()

                return jsonify(
                    {'success': True, 'message': 'Processamento autorizado e iniciado.', 'file_id': new_file.id})
            else:
                new_file = File(user_id=current_user.id, filename=filename, s3_key='',
                                status='Aguardando Pagamento', cost=cost)
                db.session.add(new_file)
                db.session.commit()

                return jsonify(
                    {'success': False, 'message': 'Saldo insuficiente. Por favor, gere um PIX para continuar.',
                     'file_id': new_file.id, 'custo': cost})

        except Exception as e:
            app.logger.error(f'Ocorreu um erro ao fazer o upload: {str(e)}')
            return jsonify({'error': f'Ocorreu um erro ao fazer o upload: {str(e)}'}), 500

    return jsonify({'error': 'Tipo de arquivo não permitido.'}), 400


@main.route('/generate_pix/<int:file_id>', methods=['POST'])
@login_required
def generate_pix(file_id):
    file = File.query.get(file_id)
    if not file or file.status != 'Aguardando Pagamento':
        return jsonify({'error': 'Arquivo não encontrado ou pagamento não necessário.'}), 400

    api_key = os.getenv('OPENPIX_API_KEY')
    headers = {
        'Authorization': f'{api_key}',
        'Content-Type': 'application/json'
    }

    valor_em_centavos = int(file.cost)

    payload = {
        "name": f"Pagamento do arquivo {file_id}",
        "correlationID": str(uuid.uuid4()),  # UUID único
        "value": valor_em_centavos,  # Valor em centavos
        "comment": f"Pagto arquivo ID {file_id}"
    }

    try:
        conn = http.client.HTTPSConnection("api.openpix.com.br")
        conn.request("POST", "/api/v1/qrcode-static", json.dumps(payload), headers)
        response = conn.getresponse()
        data = response.read()
        charge = json.loads(data.decode("utf-8"))

        app.logger.info(f'Resposta da API: {charge}')

        if 'pixQrCode' in charge and 'qrCodeImage' in charge['pixQrCode']:
            qr_code = charge['pixQrCode']['qrCodeImage']

            # Registrar a transação na tabela Transaction
            new_transaction = Transaction(
                user_id=current_user.id,
                amount=valor_em_centavos,
                file_id=file_id,
                timestamp=db.func.now(),
                status='Pendente',
                correlation_id=payload['correlationID'],
                description=f"Pagamento do arquivo {file_id}",
                payment_type="PIX",
                reference=f"Arquivo {file_id}"
            )
            db.session.add(new_transaction)
            db.session.commit()

            # Atualizar o arquivo com o QR Code gerado
            file.qr_code = qr_code
            file.status = 'Aguardando Confirmação'
            db.session.commit()

            return jsonify({'qr_code': qr_code})
        else:
            app.logger.error(f"Erro na resposta da API: {charge}")
            return jsonify({'error': 'Erro ao gerar cobrança. Verifique a resposta da API.'}), 500

    except requests.exceptions.HTTPError as http_err:
        app.logger.error(f"HTTP error occurred: {http_err}")
        return jsonify({'error': 'Erro ao gerar cobrança. Verifique a resposta da API.'}), 500
    except Exception as err:
        app.logger.error(f"Other error occurred: {err}")
        return jsonify({'error': 'Erro ao gerar cobrança. Verifique a resposta da API.'}), 500


@main.route('/get_pix/<int:file_id>', methods=['GET'])
@login_required
def get_pix(file_id):
    file = File.query.get(file_id)
    if not file or not file.qr_code:
        return jsonify({'error': 'QR Code não encontrado para este arquivo.'}), 404

    return jsonify({'qr_code': file.qr_code})


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
        # 'Authorization': f'{api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "name": "Webhook_Prod",
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
            file = File.query.get(transaction.file_id)
            if file:
                file.status = 'Pagamento Confirmado'
                db.session.commit()

                if not check_processing_server_status():
                    if not start_processing_server(os.getenv('EC2_INSTANCE_ID')):
                        return jsonify({'error': 'Erro ao iniciar o servidor de processamento.'}), 500

    return jsonify({'status': 'success'}), 200
