""" Módulo com as rotas da aplicação. """

# Importações necessárias para as rotas
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, login_user
from werkzeug.security import check_password_hash

from .models import User, File, Transaction
from . import db

# Criação de um Blueprint para as rotas principais
main = Blueprint('main', __name__)


@main.route('/')
@login_required
def index():
    # Obtém os arquivos do usuário logado
    files_in_process = File.query.filter_by(user_id=current_user.id, status='Iniciando').all()
    files_ready = File.query.filter_by(user_id=current_user.id, status='Pronto').all()
    # Obtém os créditos do usuário logado
    credits = current_user.credits
    # Renderiza o template passando os arquivos em processamento, os arquivos prontos e os créditos
    return render_template('index.html', files_in_process=files_in_process, files_ready=files_ready, credits=credits)


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
    """
    Rota para a página que lista todas as transações do usuário.
    """
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
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


@main.route('/upload_link', methods=['POST'])
@login_required
def upload_link():
    """
    Rota para processar o envio de um link pelo usuário, consumindo um crédito.
    """
    link = request.form.get('link')
    if current_user.credits < 1:
        flash('Você não tem créditos suficientes!', 'danger')
        return redirect(url_for('main.index'))

    new_file = File(link=link, status='Iniciando', user_id=current_user.id)
    db.session.add(new_file)
    current_user.credits -= 1

    new_transaction = Transaction(user_id=current_user.id, amount=-1,
                                  description=f'Consumo de crédito para o link: {link}')
    db.session.add(new_transaction)
    db.session.commit()

    flash('Link enviado para processamento!', 'success')
    return redirect(url_for('main.index'))


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
    credits = int(request.form.get('credits'))
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
