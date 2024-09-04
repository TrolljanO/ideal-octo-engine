from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from .models import User
from . import db
from flask_jwt_extended import create_access_token

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.json.get('email')
    password = request.json.get('password')

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({'message': 'Por favor, verifique seus dados e tente novamente.'}), 401

    # Gera o token JWT
    access_token = create_access_token(identity=user.id)

    return jsonify({
        'message': 'Login realizado com sucesso!',
        'access_token': access_token
    }), 200

@auth.route('/signup', methods=['GET'])
def signup():
    return render_template('signup.html')

@auth.route('/signup', methods=['POST'])
def signup_post():
    email = request.json.get('email')
    name = request.json.get('username')
    password = request.json.get('password')

    user = User.query.filter_by(email=email).first()

    if user:
        return jsonify({'message': 'Este e-mail já está em uso'}), 409

    new_user = User(
        email=email,
        username=name,
        password=generate_password_hash(password, method='pbkdf2:sha256')
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Usuário criado com sucesso'}), 201


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
