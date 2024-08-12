from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
import pymysql
import logging
from logging.handlers import RotatingFileHandler

pymysql.install_as_MySQLdb()
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

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

    with app.app_context():
        from app.routes import main
        from app.auth import auth

        app.register_blueprint(main)
        app.register_blueprint(auth)

    return app
