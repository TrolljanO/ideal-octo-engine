import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from config import Config
import pymysql
from flask_jwt_extended import JWTManager

load_dotenv()
pymysql.install_as_MySQLdb()

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['JWT_SECRET_KEY'] = 'a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a'  # Altere isso para algo mais seguro!

    # Inicializar CORS
    CORS(app, supports_credentials=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)


    jwt = JWTManager(app)

    # Configuração de logging
    if not app.debug:
        # Log de erros
        error_handler = RotatingFileHandler('error.log', maxBytes=1024 * 1024 * 100, backupCount=10)
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
        error_handler.setFormatter(error_formatter)
        app.logger.addHandler(error_handler)

        # Log de informações
        info_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
        info_handler.setLevel(logging.INFO)
        info_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
        info_handler.setFormatter(info_formatter)
        app.logger.addHandler(info_handler)

    # Registrar blueprints
    with app.app_context():
        from app.routes import main
        from app.auth import auth

        app.register_blueprint(main)
        app.register_blueprint(auth)

    return app

# Mover a execução da aplicação para fora da função create_app
if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    app = create_app()
    app.run(debug=True)
