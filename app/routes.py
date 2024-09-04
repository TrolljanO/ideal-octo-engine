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
from functools import wraps
import boto3
from flask_jwt_extended import jwt_required, get_jwt_identity

load_dotenv()

main = Blueprint('main', __name__)

BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'zip,rar').split(','))
instance_id = os.getenv('EC2_INSTANCE_ID')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_processing_server_status():
    try:
        ec2_client = boto3.client('ec2', region_name=os.getenv('AWS_REGION'))
        response = ec2_client.describe_instance_status(InstanceIds=[os.getenv('EC2_INSTANCE_ID')])

        if response['InstanceStatuses']:
            instance_state = response['InstanceStatuses'][0]['InstanceState']['Name']
            if instance_state == 'running':
                return True
            else:
                return False
        else:
            return False

    except Exception as e:
        app.logger.error(f"Erro ao verificar status da instância: {e}")
        return False


def start_processing_server():
    try:
        ec2_client = boto3.client(
            'ec2',
            region_name=os.getenv('AWS_DEFAULT_REGION'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        instance_id = os.getenv('EC2_INSTANCE_ID')
        response = ec2_client.start_instances(InstanceIds=[instance_id])
        app.logger.info(f"Iniciando a instância: {instance_id}")
        return True
    except Exception as e:
        app.logger.error(f"Erro ao iniciar o servidor de processamento: {e}")
        return False


def validate_json_request(required_fields):
    data = request.get_json()
    if not data:
        return None, jsonify({'error': 'Dados JSON ausentes.'}), 400

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return None, jsonify({'error': f'Campos faltando: {", ".join(missing_fields)}'}), 400

    return data, None


def error_response(message, status_code=400):
    return jsonify({'error': message}), status_code


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return error_response('Permissão negada.', 403)
        return f(*args, **kwargs)
    return decorated_function


@main.route('/api/limpa-pasta', methods=['GET'])
@jwt_required()  # Protege a rota
def index_limpa_pasta():
    user_id = get_jwt_identity()  # Obtém a identidade do usuário a partir do token JWT
    user = User.query.get(user_id)

    return jsonify({
        'message': 'Bem-vindo ao serviço Limpa Pasta',
        'user': user.username,
        'credits': user.credits
    })

@main.route('/api/finance', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id = get_jwt_identity()
    transactions = Transaction.query.filter_by(user_id=user_id).all()

    return jsonify({
        'transactions': [{
            'timestamp': t.timestamp,
            'description': t.description,
            'amount': t.amount,
            'status': t.status
        } for t in transactions]
    })

@main.route('/finance', methods=['GET', 'POST'])
@login_required
def finance():
    if request.method == 'POST':
        amount = request.form.get('amount')
        user = current_user

        if not amount.isdigit():
            return error_response('Valor inválido. Insira um número inteiro.')

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
                return error_response('Erro ao gerar cobrança. Verifique a resposta da API.', 500)

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
            return error_response('Erro ao gerar cobrança. Verifique a API Key e os parâmetros.', 500)
        except Exception as err:
            app.logger.error(f"Other error occurred: {err}")
            return error_response('Erro ao gerar cobrança. Verifique a API Key e os parâmetros.', 500)

    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('finance.html', transactions=transactions)


@main.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return error_response('Nenhum arquivo foi enviado.')

    file = request.files['file']

    if file.filename == '':
        return error_response('Nenhum arquivo foi selecionado.')

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex}_{original_filename}"

        try:
            with zipfile.ZipFile(BytesIO(file.read()), 'r') as zip_ref:
                num_folders = sum(1 for z in zip_ref.namelist() if z.endswith('/'))
            cost = num_folders * 100

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
                                status='Em Processamento', cost=cost, statusPago=True)
                db.session.add(new_file)
                db.session.commit()

                start_processing_server()

                return jsonify(
                    {'success': True, 'message': 'Processamento autorizado e iniciado.', 'file_id': new_file.id})
            else:
                new_file = File(user_id=current_user.id, filename=filename, s3_key='',
                                status='Aguardando Pagamento', cost=cost, statusPago=False)
                db.session.add(new_file)
                db.session.commit()

                return jsonify(
                    {'success': False, 'message': 'Saldo insuficiente. Por favor, gere um PIX para continuar.',
                     'file_id': new_file.id, 'custo': cost})

        except Exception as e:
            app.logger.error(f'Ocorreu um erro ao fazer o upload: {str(e)}')
            return error_response(f'Ocorreu um erro ao fazer o upload: {str(e)}', 500)

    return error_response('Tipo de arquivo não permitido.')

@main.route('/files', methods=['GET'])
@login_required
def get_uploaded_files():
    files_in_process = File.query.filter_by(user_id=current_user.id).order_by(File.upload_date.desc()).all()
    files_list = [
        {
            'id': file.id,
            'filename': file.filename,
            'status': file.status,
            'cost': file.cost,
            'statusPago': file.statusPago,
            'upload_date': file.upload_date
        }
        for file in files_in_process
    ]
    return jsonify({'files': files_list}), 200

@main.route('/generate_pix/<int:file_id>', methods=['POST'])
@login_required
def generate_pix(file_id):
    file = File.query.get(file_id)
    if not file or file.status != 'Aguardando Pagamento':
        return error_response('Arquivo não encontrado ou pagamento não necessário.')

    api_key = os.getenv('OPENPIX_API_KEY')
    headers = {
        'Authorization': f'{api_key}',
        'Content-Type': 'application/json'
    }

    valor_em_centavos = int(file.cost)
    if valor_em_centavos <= 0:
        return error_response('O valor do arquivo não é válido.', 400)

    payload = {
        "name": f"Pagamento do arquivo {file_id}",
        "correlationID": str(uuid.uuid4()),
        "value": valor_em_centavos,
        "comment": f"Pagto arquivo ID {file_id}"
    }

    try:
        conn = http.client.HTTPSConnection("api.openpix.com.br")
        conn.request("POST", "/api/v1/qrcode-static", json.dumps(payload), headers)
        response = conn.getresponse()

        if response.status != 200:  # Verifica se a resposta HTTP é de sucesso
            return error_response(f"Erro ao gerar o PIX. Status: {response.status}", response.status)

        data = response.read()
        charge = json.loads(data.decode("utf-8"))

        app.logger.info(f'Resposta da API: {charge}')

        if 'pixQrCode' in charge and 'qrCodeImage' in charge['pixQrCode']:
            qr_code = charge['pixQrCode']['qrCodeImage']

            # Registro da transação
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

            # Atualizar o status do arquivo com o QR Code gerado
            file.qr_code = qr_code
            file.status = 'Aguardando Confirmação'
            db.session.commit()

            return jsonify({'qr_code': qr_code})
        else:
            app.logger.error(f"Campo 'pixQrCode' ou 'qrCodeImage' não encontrado na resposta da API: {charge}")
            return error_response('Erro ao gerar cobrança. Verifique a resposta da API.', 500)

    except requests.exceptions.ConnectionError as conn_err:
        app.logger.error(f"Erro de conexão: {conn_err}")
        return error_response('Erro ao conectar à API OpenPix.', 500)

    except requests.exceptions.Timeout as timeout_err:
        app.logger.error(f"Erro de timeout: {timeout_err}")
        return error_response('A requisição para a API OpenPix demorou muito para responder.', 500)

    except requests.exceptions.HTTPError as http_err:
        app.logger.error(f"Erro HTTP: {http_err}")
        return error_response('Erro ao gerar cobrança. Verifique a API Key e os parâmetros.', 500)

    except Exception as err:
        app.logger.error(f"Outro erro: {err}")
        return error_response('Ocorreu um erro inesperado ao gerar o PIX.', 500)


@main.route('/get_pix/<int:file_id>', methods=['GET'])
@login_required
def get_pix(file_id):
    file = File.query.get(file_id)
    if not file or not file.qr_code:
        return error_response('QR Code não encontrado para este arquivo.', 404)

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
        return error_response(f'HTTP error occurred: {http_err}', 500)
    except Exception as err:
        return error_response(f'Other error occurred: {err}', 500)


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
                file.statusPago = True
                db.session.commit()

                if not check_processing_server_status():
                    if not start_processing_server():
                        return error_response('Erro ao iniciar o servidor de processamento.', 500)

    return jsonify({'status': 'success'}), 200
