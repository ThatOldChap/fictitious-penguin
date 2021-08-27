import enum, math

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
    return round((value / total) * 100, 1)