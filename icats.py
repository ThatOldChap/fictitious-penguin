from app import create_app, db
from app.models import TestPoint, Channel, Group, Job, Project, CalibrationRecord
from app.models import Client, User, TestEquipment, TestEquipmentType

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
        'Client': Client,
        'User': User,
        'TestEquipment': TestEquipment,
        'TestEquipmentType': TestEquipmentType,
        'CalibrationRecord': CalibrationRecord
    }

'''
@app.context_processor
def utility_processor():
    return dict(round=round)
'''