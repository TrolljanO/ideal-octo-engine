from flask_login import UserMixin
from app import login
from datetime import datetime
from sqlalchemy.sql import func
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    credits = db.Column(db.Integer, default=0)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(255), nullable=True)
    files = db.relationship('File', backref='user', lazy=True)  # Relação com File

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=func.now())
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    payment_type = db.Column(db.String(50), nullable=True)
    reference = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Pendente')
    correlation_id = db.Column(db.String(255), nullable=False)

    def formatted_amount(self):
        return f"R$ {self.amount / 100:.2f}"

from datetime import datetime
from . import db

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Iniciando')
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    s3_key = db.Column(db.String(255), nullable=False)
    download_link = db.Column(db.String(255), nullable=True)
    cost = db.Column(db.Float, nullable=True)
    qr_code = db.Column(db.Text, nullable=True)
    statusPago = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, user_id, filename, s3_key, status='Iniciando', cost=None, statusPago=False):
        self.user_id = user_id
        self.filename = filename
        self.s3_key = s3_key
        self.status = status
        self.cost = cost
        self.statusPago = statusPago

    def __repr__(self):
        return f'<File {self.filename}>'

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
