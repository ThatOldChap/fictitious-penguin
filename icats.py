from app import create_app, db
from app.models import TestPoint, Channel, Group, Job, Project, Client

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
        'Client': Client
    }

'''
@app.context_processor
def utility_processor():
    return dict(round=round)
'''