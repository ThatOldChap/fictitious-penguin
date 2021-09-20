from app import create_app, db
from app.models import *
from app.utils import *

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


@app.context_processor
def utility_processor():

    def measurement_types():
        return [measurement_type.value for measurement_type in MeasurementType]

    def eng_units():
        return [unit.value for unit in EngUnits]

    def error_types():
        return [error_type.value for error_type in ErrorType]

    return dict(
        measurement_types=measurement_types,
        eng_units=eng_units,
        error_types=error_types
    )
