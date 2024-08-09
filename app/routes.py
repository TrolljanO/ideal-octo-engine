from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import User, FileLog, Transaction
from . import db
from config import s3
import zipfile
from io import BytesIO

# Criação de um Blueprint para as rotas principais
main = Blueprint('main', __name__)

# Configurar o nome do bucket S3 e o caminho permitido para uploads
BUCKET_NAME = 'l769ab'
ALLOWED_EXTENSIONS = {'zip', 'rar', 'RAR', 'ZIP'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/')
@login_required
def index():
    files_in_process = FileLog.query.filter_by(user_id=current_user.id).order_by(FileLog.upload_date.desc()).all()
    files_ready = FileLog.query.filter_by(user_id=current_user.id, status='Pronto').all()

    return render_template('index.html',
                           files_in_process=files_in_process,
                           files_ready=files_ready,
                           credits=current_user.credits)


@main.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('Nenhum arquivo foi enviado.', 'danger')
        return redirect(url_for('main.index'))

    file = request.files['file']

    if file.filename == '':
        flash('Nenhum arquivo foi selecionado.', 'danger')
        return redirect(url_for('main.index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        s3_key = f"{current_user.id}/{filename}"
        try:
            # Upload do arquivo para o S3
            s3.upload_fileobj(
                file,
                BUCKET_NAME,
                s3_key,
                ExtraArgs={"ContentType": file.content_type}
            )

            # Recalcular o número de pastas no ZIP para definir o custo
            file.seek(0)
            with zipfile.ZipFile(BytesIO(file.read()), 'r') as zip_ref:
                num_folders = sum(1 for z in zip_ref.namelist() if z.endswith('/'))

            cost = num_folders * 1.00  # Exemplo de cálculo: R$1,00 por pasta

            # Registrar no banco de dados
            new_log = FileLog(user_id=current_user.id, filename=filename, s3_key=s3_key, status='Aguardando Autorização', cost=cost)
            db.session.add(new_log)
            db.session.commit()

            # Enviar custo ao usuário
            flash(f'O custo é R$ {cost:.2f}. Deseja autorizar?', 'info')
            session['file_id'] = new_log.id

            return jsonify({'custo': cost, 'num_folders': num_folders, 'file_id': new_log.id})

        except Exception as e:
            app.logger.error(f'Ocorreu um erro ao fazer o upload: {str(e)}')
            flash(f'Ocorreu um erro ao fazer o upload: {e}', 'danger')
            return redirect(url_for('main.index'))

    return render_template('index.html')


@main.route('/authorize_process', methods=['POST'])
@login_required
def authorize_process():
    file_id = request.form['file_id']
    file_log = FileLog.query.get(file_id)

    if current_user.credits >= file_log.cost:
        current_user.credits -= file_log.cost
        file_log.status = 'Autorizado'
        db.session.commit()
        flash('Processo autorizado e saldo debitado.', 'success')
    else:
        flash('Saldo insuficiente para autorizar o processo.', 'danger')

    return redirect(url_for('main.index'))

@main.route('/cancel_process', methods=['POST'])
@login_required
def cancel_process():
    file_id = request.form['file_id']
    file_log = FileLog.query.get(file_id)
    file_log.status = 'Cancelado'
    db.session.commit()
    flash('Processo cancelado.', 'warning')

    return redirect(url_for('main.index'))

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@main.route('/transactions')
@login_required
def transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('transactions.html', transactions=transactions)


@main.route('/finance')
@login_required
def finance():
    if not current_user.is_admin:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('main.index'))

    transactions = Transaction.query.all()
    return render_template('finance.html', transactions=transactions)


@main.route('/calculate_cost', methods=['POST'])
@login_required
def calculate_cost():
    file_id = request.form['file_id']

    s3_key = request.form['s3_key']

    # Função para calcular o número de pastas (isso deve ser implementado)
    num_pastas = calcular_numero_de_pastas(s3_key)

    custo = num_pastas * 1.00  # Exemplo: R$ 1,00 por pasta

    # Atualize o banco de dados com o custo
    file_log = FileLog.query.get(file_id)
    file_log.cost = custo
    db.session.commit()

    return jsonify({'custo': custo})