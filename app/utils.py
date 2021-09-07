import enum, math
from app import db
from datetime import datetime

class TestResult(enum.Enum):
    UNTESTED = "Untested"
    PASS = "Pass"
    FAIL = "Fail"
    # POST = "Post"

class Status(enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In-Progress"
    COMPLETE = "Complete"

class MeasurementType(enum.Enum):
    ANALOGUE_INPUT = "Analogue Input"
    ANALOGUE_OUTPUT = "Analogue Output"
    DIGITAL_INPUT = "Digital Input"
    DIGITAL_OUTPUT = "Digital Output"
    FREQUENCY = "Frequency"
    TEMPERATURE = "Temperature"
    PRESSURE = "Pressure"

class EngUnits(enum.Enum):
    VOLTS = "V"
    MILLIAMPS = "mA"
    DEGREES_CELSIUS = "degC"
    HERTZ = "Hz"
    OHMS = "Ohms"
    PSI = "psi"

class ErrorType(enum.Enum):
    ENG_UNITS = 'Eng Units'
    PERCENT_FULL_SCALE = f'%FS'
    PERCENT_READING = '%RDG'    

class JobStage(enum.Enum):
    IN_HOUSE = "In-House"
    ON_SITE = "On-Site"

class JobPhase(enum.Enum):
    COMMISSIONING = "Commissioning"
    ATP = "ATP"

class TestPointListType(enum.Enum):
    STANDARD = "Standard"
    CUSTOM = "Custom"

class StandardTestEquipmentTypes(enum.Enum):
    BRIDGE_SIMULATOR = "Bridge Simulator"
    DC_VOLTAGE_SOURCE = "DC Voltage Source"
    MULTIFUNCTION_CALIBRATOR = "Multifunction Calibrator"
    SIGNAL_SOURCE = "Signal Source"
    OSCILLOSCOPE = "Oscilloscope"
    DIGITAL_MULTIMETER = "Digital Multimeter"
    DIGITAL_PRESSURE_GAUGE = "Digital Pressure Gauge"
    RESOLVER_SIMULATOR = "Resolver Simulator"
    DECADE_BOX = "Decade Box"


# Returns None if a value is empty
def none_if_empty(value):
    return None if value == "" else value


# Calculates some statistics on a list fo channels
def channel_stats(channels):

        # Statistics tracking variables
        num_untested = 0
        num_passed = 0
        num_failed = 0
        num_in_progress = 0

        # Tally up the status
        for channel in channels:

            status = channel.status

            if status == TestResult.UNTESTED.value:
                num_untested += 1
            elif status == TestResult.PASS.value:
                num_passed += 1
            elif status == TestResult.FAIL.value:
                num_failed += 1
            elif status == Status.IN_PROGRESS.value:
                num_in_progress += 1
        
        # Compile and return the results
        return {
            TestResult.UNTESTED.value: num_untested,
            TestResult.PASS.value: num_passed,
            TestResult.FAIL.value: num_failed,
            Status.IN_PROGRESS.value: num_in_progress
        }


# Returns the channel progress for a given set of channels
def channel_progress(item):

    # Get the channel stats
    stats = item.channel_stats()
    num_channels = item.num_channels()

    if num_channels == 0:
        return {
        "percent_untested": 100,
        "percent_passed": 0,
        "percent_failed": 0,
        "percent_in_progress": 0
        }
    else:
        return {
            "percent_untested": calc_percent(stats[TestResult.UNTESTED.value], num_channels),
            "percent_passed": calc_percent(stats[TestResult.PASS.value], num_channels),
            "percent_failed": calc_percent(stats[TestResult.FAIL.value], num_channels),
            "percent_in_progress": calc_percent(stats[Status.IN_PROGRESS.value], num_channels)
        }


# Calculates the percent value of a number and out of its total
def calc_percent(value, total):
    return 0 if (total == 0) else round((value / total) * 100)

# Generates a list of tuples for use in a numeric SelectField form field
def number_list_choices(last_num, num_digits):
    num_list = []
    for i in range(1, last_num+1):
        if num_digits == 1:
            value = i
        elif num_digits == 2:
            value = f'{i:02d}'
        elif num_digits == 3:
            value = f'{i:03d}'            
        num_list.append((i, value))
    return num_list


# Prepopulate the database with the StandardTestEquipmentTypes
def addStandardTestEquipmentTypes():
    
    # Import the Model directly here to avoid a circular import
    from app.models import TestEquipmentType

    # New Equipment list
    new_equipment_types = []

    # Compile a list of the existing TestPointType items in the database
    existing_equipment = [t.name for t in TestEquipmentType.query.all()]

    # Create new TestEquipmentTypes
    for test_equipment_type in StandardTestEquipmentTypes:

        # Check to make sure an existing TestEquipmentType doesn't already exist
        if test_equipment_type.value in existing_equipment:
            continue

        new_type = TestEquipmentType(name=test_equipment_type.value)
        db.session.add(new_type)
        new_equipment_types.append(new_type.name)
    
    # Save the changes
    db.session.commit()
    print(f'Successfully added the following TestEquipmentTypes:\n{new_equipment_types}')

# Pre-populate the database with test data
def initDbForTest():

    from app.models import User, Client, Project, Job, Group, TestEquipment, TestEquipmentType, CalibrationRecord

    # Create some Users
    u1 = User(username='Michael', email='michael@example.com')
    u1.set_password('test')
    u2 = User(username='Natalie', email='natalie@example.com')
    u2.set_password('test')
    u3 = User(username='Eric', email='eric@example.com')
    u3.set_password('test')
    u4 = User(username='John', email='john@example.com')
    u4.set_password('test')    
    db.session.add_all([u1, u2, u3, u4])
    db.session.commit()

    # Create some Clients
    c1 = Client(name="Rolls-Royce")
    c2 = Client(name="Pratt & Whitney")
    c3 = Client(name="SEBW")
    db.session.add_all([c1, c2, c3])
    db.session.commit()

    # Create some Projects
    p1 = Project(name='Test Bed 80', number='0542', client_id=c1.id)
    p2 = Project(name='RTS Development', number='0545', client_id=c1.id)
    p3 = Project(name='UTRC Compressor', number='0529', client_id=c2.id)
    p4 = Project(name='Aero E-Fan', number='0551', client_id=c2.id)
    p5 = Project(name='Core 2 Facility', number='1051', client_id=c3.id)
    p6 = Project(name='High Altitude Facility', number='1003', client_id=c3.id)
    db.session.add_all([p1, p2, p3, p4, p5, p6])
    db.session.commit()

    # Create some Jobs for the Projects
    for p in Project.query.all():
        j1 = Job(project_id=p.id, name="TDAS", stage="In-House", phase="Commissioning")
        j2 = Job(project_id=p.id, name="TDAS", stage="On-Site", phase="Commissioning")
        j3 = Job(project_id=p.id, name="TDAS", stage="On-Site", phase="ATP")
        db.session.add_all([j1, j2, j3])
    db.session.commit()

    # Create some groups for the Jobs
    for j in Job.query.all():
        g1 = Group(name='Liquid/Air Pressures', job_id=j.id)
        g2 = Group(name='Speeds', job_id=j.id)
        g3 = Group(name='Vibrations', job_id=j.id)
        db.session.add_all([g1, g2, g3])
    db.session.commit()

    # Create the default TestEquipmentTypes
    addStandardTestEquipmentTypes()
    
    # Create some starting TestEquipment
    count = 1
    for t in TestEquipmentType.query.all():
        t1 = TestEquipment(
            name=t.name,
            manufacturer='ACME Co.',
            model_num='123456' + str(count*10),
            serial_num='000000' + str(count*10),
            asset_id='MDS 1' + str(count*10)
        )
        db.session.add(t1)
        count += 1
    db.session.commit()

    # Add some calibration records for each TestEquipment
    for t in TestEquipment.query.all():
        dt1 = datetime(2021, 4, 4)
        dt2 = datetime(2021, 11, 18)
        dt3 = datetime(2022, 3, 29)
        c1 = CalibrationRecord(test_equipment_id=t.id,
            calibration_date=dt1,
            calibration_due_date=dt2)
        c2 = CalibrationRecord(test_equipment_id=t.id,
            calibration_date=dt1,
            calibration_due_date=dt3)
        t.add_calibration_record(c1)
        t.add_calibration_record(c2)
        test_equipment_type = TestEquipmentType.query.filter_by(name=t.name).first()
        test_equipment_type.add_test_equipment(t)
    db.session.commit()