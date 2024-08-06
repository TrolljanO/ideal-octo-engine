"""
Database models for the Flask app.
"""
from flask_login import UserMixin
from app import login
from datetime import datetime
import uuid
from sqlalchemy.sql import func
from . import db

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
    timestamp = db.Column(db.DateTime, default=func.now())
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Iniciando')
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    s3_key = db.Column(db.String(255), nullable=False)
    download_link = db.Column(db.String(255), nullable=True)  # Pode ser null até que o link seja gerado

    def __init__(self, user_id, filename, s3_key):
        self.user_id = user_id
        self.filename = filename
        self.s3_key = s3_key

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class FileLog(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    s3_key = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Iniciando')

    def __init__(self, user_id, filename, s3_key, status='Iniciando'):
        self.user_id = user_id
        self.filename = filename
        self.s3_key = s3_key
        self.status = status