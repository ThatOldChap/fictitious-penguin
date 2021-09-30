import os, psycopg2
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):

    # SQLAlchemy Database setup
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Bootstrap setup
    BOOTSTRAP_BOOTSWATCH_THEME = 'flatly'
    # BOOTSTRAP_BOOTSWATCH_THEME = 'zephyr'
    # BOOTSTRAP_BOOTSWATCH_THEME = 'minty'
    # BOOTSTRAP_BOOTSWATCH_THEME = 'sandstone'

    # Mail server setup
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME =  os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # Logging Setup
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

    # Auth stuff
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'potato-cactus'
    ADMINS = ['michaeljchap@gmail.com']

    # Pre-emptive Pagination Setup
    ITEMS_PER_PAGE = 3

    # File Directories
    if basedir == '/app':
        # Removes the additional '/app' from the basedir on Heroku
        CHANNEL_REPORT_DIRECTORY = basedir + '/static/job_reports/'
    else:
        CHANNEL_REPORT_DIRECTORY = basedir + '/app/static/job_reports/'