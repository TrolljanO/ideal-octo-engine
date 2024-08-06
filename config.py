import os

base_dir = os.path.abspath(os.path.dirname(__file__))


class Config:

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(base_dir, 'instance', 'limpapasta.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = '-q9jKRX-1koTFm5_gsPOSsdkxFpBMPifn_lF4VeORJKmNnjw_sLrKqMcbhgmu5uotcw'  # Substitua 'your_secret_key' por uma chave secreta real