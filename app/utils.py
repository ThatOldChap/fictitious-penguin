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
    VOLTS_AC = "VAC"
    VOLTS_DC = "VDC"
    VOLTS_MILLI = "mV"
    AMPS = "A"    
    AMPS_MILLI = "mA"
    DEGREES_CELSIUS = "degC"
    DEGREES_FAHRENHEIT = "degF"
    KELVIN = "K"
    HERTZ = "Hz"
    HERTZ_KILO = "kHz"
    OHMS = "Ohms"
    PSI = "psi"

class ErrorType(enum.Enum):
    ENG_UNITS = 'Eng Units'
    PERCENT_FULL_SCALE = f'%FS'
    PERCENT_READING = '%RDG'

class CompanyCategory(enum.Enum):
    SUPPLIER = 'Supplier'
    CLIENT = 'Client'

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
def number_list_choices(first_num, last_num, num_digits):
    num_list = []
    for i in range(first_num, last_num+1):
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
def init_test_db():

    from app.models import User, Company, Project, Job, Group, TestEquipment
    from app.models import TestEquipmentType, CalibrationRecord, ApprovalRecord

    # Create some Clients
    client_names = ['Rolls-Royce', 'Pratt & Whitney', 'SEBW']    
    for i in range(len(client_names)):
        c = Company(
            name=client_names[i],
            category=CompanyCategory.CLIENT.value
        )
        db.session.add(c)
    db.session.commit()

    # Create some Suppliers
    supplier_names = ['MDS', 'MDS UK']
    for i in range(len(supplier_names)):
        c = Company(
            name=supplier_names[i],
            category=CompanyCategory.SUPPLIER.value
        )
        db.session.add(c)
    db.session.commit()

    # Get all the created Companies
    clients = Company.clients()
    suppliers = Company.suppliers()

    # Create some Client Users
    client_user_first_names = ['Steve', 'Joe', 'Darren', 'Paul']    
    client_user_last_names = ['Chew', 'Brook', 'Till', 'Brass']    
    for c in clients:
        for i in range(len(client_user_first_names)):
            first_name = client_user_first_names[i]
            last_name = client_user_last_names[i]
            username = first_name + last_name + str(c.id)
            u = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=username + '@example.com',
                company_id=c.id
            )
            u.set_password('test')
            db.session.add(u)
            db.session.commit()
            c.add_employee(u)
    db.session.commit()
    
    # Create some Supplier Users
    supplier_user_first_names = ['Michael', 'Tyler', 'Ethan', 'Troy']
    supplier_user_last_names = ['Chaplin', 'Seal', 'Stevens', 'Schultz']
    for s in suppliers:
        for i in range(len(supplier_user_first_names)):
            first_name = supplier_user_first_names[i]
            last_name = supplier_user_last_names[i]
            username = first_name + last_name + str(s.id)
            u = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=username + '@example.com',
                company_id=s.id,
            )
            u.set_password('test')
            db.session.add(u)
            db.session.commit()
            s.add_employee(u)
    db.session.commit()

    # Get the main supplier
    supplier = suppliers[0]

    # Create some Projects
    project_names = [['Test Bed 80', 'RTS Development'], ['UTRC Compressor', 'Aero E-Fan'],
        ['Core 2 Facility', 'High Altitude Facility']]
    project_numbers = [['0542', '0545'], ['0529', '0551'], ['1051', '1003']]    
    for i in range(len(clients)):
        for j in range(len(project_names[0])):
            p = Project(
                name=project_names[i][j],
                number=project_numbers[i][j]
            )
            db.session.add(p)
            db.session.commit()
            p.add_company(clients[i])
            p.add_company(supplier)
            p.add_members(clients[i].employees.all())
            p.add_members(supplier.employees.all())
            db.session.commit()
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