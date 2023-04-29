from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel, _
from config import config
from datetime import timedelta
from flask_mail import Mail
from flask_socketio import SocketIO
import re
email_regex = re.compile('^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
name_regex = re.compile('^[a-z A-Z]+$')
price_letters_regex = re.compile('^[a-zA-Z-]')
phone_number_regex = re.compile('^[\+]?[(]?[0-9]{2}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,7}$')

app = Flask(__name__)
database = SQLAlchemy()
login_manager = LoginManager()
babel = Babel()
mail = Mail()
socketio=SocketIO()

def create_app(config_name):
    app.config.from_object(config[config_name])
    app.permanent_session_lifetime = timedelta(hours = 24)
    database.init_app(app)
    socketio.init_app(app)
    login_manager.login_view="auth_bp.login"

    login_manager.login_message= _('Vous devez vous connecter afin d\'utiliser ce service')
    login_manager.login_message_category="warning"
    login_manager.init_app(app)

    babel.init_app(app)
    mail.init_app(app)
    from root.admin import admin_bp
    app.register_blueprint(admin_bp)
    from root.auth import auth_bp
    app.register_blueprint(auth_bp)

    from root.achats import purchases_bp
    app.register_blueprint(purchases_bp)

    from root.ventes import sales_bp
    app.register_blueprint(sales_bp)

    from root.socket_notifications import socket_notification_bp
    app.register_blueprint(socket_notification_bp)

    return app

