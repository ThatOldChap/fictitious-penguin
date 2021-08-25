import enum

class TestResult(enum.Enum):
    UNTESTED = "Untested"
    PASS = "Pass"
    FAIL = "Fail"    
    # POST = "Post"

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

# Returns None if a value is empty
def none_if_empty(value):
    return None if value == "" else value