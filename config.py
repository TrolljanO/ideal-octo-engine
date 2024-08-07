import os
from dotenv import load_dotenv
import boto3

base_dir = os.path.abspath(os.path.dirname(__file__))

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(base_dir, 'instance', 'limpapasta.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY')

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)
