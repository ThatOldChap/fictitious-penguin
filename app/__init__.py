import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_babel import Babel, format_decimal
from config import Config

# Instantiate all the main dependencies
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()
babel = Babel()

# Setup the LoginManager for the all the user authentication
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page'

# Import all the models to allow Alembic/Flask-Migrate to recongize schema changes better
from app.models import TestPoint, Channel, Group, Job, Project, TestEquipment, TestEquipmentType
from app.models import User, Company, CalibrationRecord, ApprovalRecord, ChannelEquipmentRecord

# Initializing the modules within the app
def create_app(config_class=Config):
    # Assign a config to the app instance
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Add the zip function into the jinja template functionality
    app.jinja_env.globals.update(zip=zip)
    app.jinja_env.filters['format_decimal'] = format_decimal    

    # Pass the application context to each of the initialize dependencies
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)

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

            # Setup a stream handler
            stream_handler = setup_stream_handler(logging.DEBUG)
            app.logger.addHandler(stream_handler)
            
        else:
            # Setup a file handler
            file_handler = setup_file_handler(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Starting ICATS application...')

    # Set by using the command "export FLASK_DEBUG=1"
    elif app.debug:

        # Setup the loggers
        file_handler = setup_file_handler(logging.DEBUG)
        stream_handler = setup_stream_handler(logging.DEBUG)

        # Add the loggers to the application
        app.logger.addHandler(file_handler)
        app.logger.addHandler(stream_handler)

    return app


# Helper function to setup a logger
def setup_file_handler(level):

    # Setup a directory to store any log files
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Define the file handler and add the proper formatting to the log messages
    file_handler = RotatingFileHandler('logs/icats.log', maxBytes=10240, backupCount=2)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(level)

    return file_handler

def setup_stream_handler(level):

    # Setup the stream handler for the stdout messages
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)

    return stream_handler


from app.models import *