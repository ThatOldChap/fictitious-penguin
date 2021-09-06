import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from config import Config

# Instantiate all the main dependencies
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()

# Setup the LoginManager for the all the user authentication
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page'

# Initializing the modules within the app
def create_app(config_class=Config):
    # Assign a config to the app instance
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Add the zip function into the jinja template functionality
    app.jinja_env.globals.update(zip=zip)

    # Import the models to allow for migrate to detect any changes
    from app.models import User, TestPoint, Channel, Group, Job, Project, Client, TestEquipment
    from app.models import TestEquipmentType, CalibrationRecord, ChannelEquipmentRecord

    # Pass the application context to each of the initialize dependencies
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)

    # Register each blueprint section
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    """ from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api') """

    if not app.debug and not app.testing:

        # Setup the mail server if defined
        if app.config['MAIL_SERVER']:

            # Setup the credentials for the mail server
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'],
                        app.config['MAIL_PASSWORD'])

            # Setup the security protocol
            secure = None
            if app.config['MAIL_USER_TLS']:
                secure()

            # Seup the mail handler
            mail_handler = SMTPHandler(
                mail_host=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='ICATS Failure',
                credentials=auth, secure=secure
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        
        # Configures the logger to the cli stdout to work with Heroku
        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger(stream_handler)
            
        else:
            # Setup a directory to store any log files
            if not os.path.exists('logs'):
                os.mkdir('logs')

            # Defines and creates the log files
            file_handler = RotatingFileHandler('logs/icats.log', maxBytes=10240, backupCount=2)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('ICATS')

    return app

from app import models