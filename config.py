import os
from dotenv import load_dotenv
import boto3
import logging

base_dir = os.path.abspath(os.path.dirname(__file__))

load_dotenv()
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY')


s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)
