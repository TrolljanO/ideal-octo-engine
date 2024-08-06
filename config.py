import os
from dotenv import load_dotenv
import boto3

base_dir = os.path.abspath(os.path.dirname(__file__))


class Config:

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(base_dir, 'instance', 'limpapasta.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '-q9jKRX-1koTFm5_gsPOSsdkxFpBMPifn_lF4VeORJKmNnjw_sLrKqMcbhgmu5uotcw'  # Substitua 'your_secret_key' por uma chave secreta real

load_dotenv()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)