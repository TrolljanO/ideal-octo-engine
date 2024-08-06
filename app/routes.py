""" Módulo com as rotas da aplicação. """

# Importações necessárias para as rotas
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, login_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from .models import User, File, Transaction
from . import db
from config import s3  # Importa o cliente S3 configurado
from .models import FileLog

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
    # Obtém os arquivos do usuário logado
    files_in_process = FileLog.query.filter_by(user_id=current_user.id).order_by(FileLog.upload_date.desc()).all()
    files_ready = File.query.filter_by(user_id=current_user.id, status='Pronto').all()

    print("Arquivos em processamento:", files_in_process)

    # Adicionar logs para depuração
    print("Arquivos em processamento:", files_in_process)
    print("Arquivos prontos:", files_ready)

    # Renderiza o template passando os arquivos em processamento, os arquivos prontos e os créditos
    return render_template('index.html',
                           files_in_process=files_in_process,
                           files_ready=files_ready,
                           credits=current_user.credits)

@main.route('/processing')
@login_required
def processing():
    logs = FileLog.query.filter_by(user_id=current_user.id).order_by(FileLog.upload_date.desc()).all()
    return render_template('processing.html', logs=logs)

@main.route('/profile')
@login_required
def profile():
    """
    Rota para a página de perfil do usuário.
    """
    return render_template('profile.html')


@main.route('/transactions')
@login_required
def transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('transactions.html', transactions=transactions)


@main.route('/finance')
@login_required
def finance():
    """
    Rota para a página financeira acessível apenas por administradores.
    """
    if not current_user.is_admin:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('main.index'))
    transactions = Transaction.query.all()
    return render_template('finance.html', transactions=transactions)


@main.route('/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
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
                # Fazer upload para o S3
                s3.upload_fileobj(
                    file,
                    BUCKET_NAME,
                    s3_key,
                    ExtraArgs={"ContentType": file.content_type}
                )

                # Registrar no banco de dados
                new_log = FileLog(user_id=current_user.id, filename=filename, s3_key=s3_key)
                db.session.add(new_log)
                db.session.commit()
                print("Arquivo registrado no banco de dados:", new_log)  # Log para depuração
                flash(f'Arquivo {filename} enviado com sucesso para o S3!', 'success')
            except Exception as e:
                flash(f'Ocorreu um erro ao fazer o upload: {e}', 'danger')
            return redirect(url_for('main.index'))

    return render_template('index.html')


@main.route('/add_credits', methods=['POST'])
@login_required
def add_credits():
    """
    Rota administrativa para adicionar créditos a qualquer usuário.
    """
    if not current_user.is_admin:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('main.index'))

    user_id = request.form.get('user_id')
    credits = request.form.get('credits')

    # Validação básica
    if not user_id or not credits:
        flash('Dados inválidos. Verifique o formulário e tente novamente.', 'danger')
        return redirect(url_for('main.finance'))

    try:
        credits = int(credits)
    except ValueError:
        flash('A quantidade de créditos deve ser um número inteiro.', 'danger')
        return redirect(url_for('main.finance'))

    user = User.query.get(user_id)
    if user:
        user.credits += credits
        new_transaction = Transaction(user_id=user.id, amount=credits, description='Adição de créditos')
        db.session.add(new_transaction)
        db.session.commit()
        flash(f'{credits} créditos adicionados para {user.username}!', 'success')
    else:
        flash('Usuário não encontrado!', 'danger')

    return redirect(url_for('main.finance'))



@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not (user and check_password_hash(user.password, password)):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        return redirect(url_for('main.index'))

    return render_template('login.html')
