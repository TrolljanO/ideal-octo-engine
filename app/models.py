"""
Database models for the Flask app.
"""
from datetime import datetime
from flask_login import UserMixin
from app import db  # Certifique-se de que 'db' é importado do módulo correto
from app import login

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    username = db.Column(db.String(1000))
    credits = db.Column(db.Integer, default=0)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(100), nullable=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    amount = db.Column(db.Integer)
    description = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.String(500))
    status = db.Column(db.String(20), default='Iniciando')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
