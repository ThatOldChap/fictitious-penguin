from app import create_app, db
from app.models import *
from app.utils import init_test_db

# Create the app instance
app = create_app()

# Injects the database model types into the flask shell instance
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'TestPoint': TestPoint,
        'Channel': Channel,
        'Group': Group,
        'Job': Job,
        'Project': Project,
        'Company': Company,
        'User': User,
        'TestEquipment': TestEquipment,
        'TestEquipmentType': TestEquipmentType,
        'CalibrationRecord': CalibrationRecord,
        'ChannelEquipmentRecord': ChannelEquipmentRecord,
        'ApprovalRecord': ApprovalRecord,
        'init_test_db': init_test_db
    }

'''
@app.context_processor
def utility_processor():
    return dict(round=round)
'''