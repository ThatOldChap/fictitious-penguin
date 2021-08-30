import enum, math
from app import db

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
    PERCENT_FULL_SCALE = f'%FS'
    PERCENT_READING = '%RDG'
    ENG_UNITS = 'Eng Units'

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

        new_type = TestEquipmentType(name=test_equipment_type.name)
        db.session.add(new_type)
        new_equipment_types.append(new_type.name)
    
    # Save the changes
    db.session.commit()
    print(f'Successfully added the following TestEquipmentTypes:\n{new_equipment_types}')