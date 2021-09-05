from datetime import datetime
from time import time
from flask import current_app
from flask_login import UserMixin
from app import db, login
from app.utils import ErrorType, TestPointListType, TestResult, Status
from app.utils import channel_stats, channel_progress, calc_percent
import jwt
from hashlib import md5
from werkzeug.security import generate_password_hash, check_password_hash


'''Many-to-Many Association Tables'''
# Stores all the Users that have access to a project
project_members = db.Table(
    'project_members', db.Model.metadata,
    db.Column('project_id', db.Integer, db.ForeignKey('project.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

# Stores all the TestEquipment used for a project
project_equipment = db.Table(
    'project_equipment', db.Model.metadata,
    db.Column('project_id', db.Integer, db.ForeignKey('project.id')),
    db.Column('test_equipment_id', db.Integer, db.ForeignKey('test_equipment.id'))
)

# Stores all the required TestEquipmentTypes for testing a channel
channel_required_equipment = db.Table(
    'channel_required_equipment', db.Model.metadata,
    db.Column('channel_id', db.Integer, db.ForeignKey('channel.id')),
    db.Column('test_equipment_type_id', db.Integer, db.ForeignKey('test_equipment_type.id'))
)


class TestPoint(db.Model):
    # Basic Info
    id = db.Column(db.Integer, primary_key=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Signal Injection Info:
    # - The raw value injected into a signal chain by a piece of calibration equipment
    # ex. A decade box injects 100.00 ohms into an RTD measurement channel
    measured_injection_value = db.Column(db.Float(16))
    nominal_injection_value = db.Column(db.Float(16))

    # Channel Test Info
    # - The value tested in the channel's final engineering units that is shown on the DAS display
    # ex. With 100.00 ohms injected, the channel's test point would be 0 degC read on a display
    measured_test_value = db.Column(db.Float(16))
    nominal_test_value = db.Column(db.Float(16))    

    # Extra Info
    measured_error = db.Column(db.Float(8))
    test_result = db.Column(db.String(12), default=TestResult.UNTESTED.value)    

    # Foreign Keys
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))

    def __repr__(self):
        return f'<TestPoint id-{self.id} for Channel {self.channel.name}>'


    def channel(self):
        return Channel.query.filter_by(id=self.channel_id).first()


    # Calculates the measured error from a signal injection
    def calc_error(self):
        return self.nominal_test_value - self.measured_test_value


    # Calculates the maximum error for a measurement based on the error type
    def calc_max_error(self):
        channel = self.channel
        error_type = channel.error_type
        max_error = channel.max_error

        # Returns an error in the engineering units provided
        # ex. max_error = +/- 0.05 VDC
        if error_type == ErrorType.ENG_UNITS.value: 
            return max_error

        # Returns an error calculated from the channel's full scale range
        # ex. max_error of 0.05 %FS is equivalent to 0.125 psi on a 0-250 psi full scale range
        elif error_type == ErrorType.PERCENT_FULL_SCALE.value:
            return channel.full_scale_range * (max_error / 100)

        # Returns an error based on the measured/read value being evaluated
        # ex. max_error of 0.1 %RDG is equivalent to 0.015 Hz at a measured value of 15 Hz
        elif error_type == ErrorType.PERCENT_READING.value:
            return self.measured_test_value * (max_error / 100)


    # Calculates the lower limit of an acceptable measurement
    def lower_limit(self):
        return self.nominal_test_value - self.calc_max_error()


    # Calculates the upper limit of an acceptable measurement
    def upper_limit(self):
        return self.nominal_test_value + self.calc_max_error()


class Channel(db.Model):
    # Basic Info
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Measurement Info
    measurement_type = db.Column(db.String(32))
    measurement_units = db.Column(db.String(16))
    min_range = db.Column(db.Float(16))
    max_range = db.Column(db.Float(16))
    full_scale_range = db.Column(db.Float(16))

    # Tolerance Info
    max_error = db.Column(db.Float(8))
    error_type = db.Column(db.String(8))

    # Signal Injection Info
    min_injection_range = db.Column(db.Float(16))
    max_injection_range = db.Column(db.Float(16))
    injection_units = db.Column(db.String(16))

    # Metrics
    status = db.Column(db.String(16), default=TestResult.UNTESTED.value)

    # Summary Info
    interface = db.Column(db.String(32))
    notes = db.Column(db.String(128))

    # Foreign Keys
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    # Relationships
    testpoints = db.relationship('TestPoint', backref='channel', lazy='dynamic')
    test_equipment = db.relationship('ChannelEquipmentRecord', back_populates='channel')
    required_test_equipment = db.relationship('TestEquipmentType',
        secondary=channel_required_equipment, backref='channel', lazy='dynamic')


    def __repr__(self):
        return f'<Channel {self.name}>'

    def group(self):
        return Group.query.filter_by(id=self.group_id).first()

    def num_testpoints(self):
        return len(self.testpoints.all())

    def measurement_range(self):
        return self.max_range - self.min_range

    def injection_range(self):
        return self.max_injection_range - self.min_injection_range

    def build_testpoint_list(self, num_testpoints, testpoint_list_type, injection_value_list, test_value_list):
        
        # Debugging variables
        num_added = 0

        # Builds a list of testpoints defined by the user when a new channel is created
        if testpoint_list_type == TestPointListType.CUSTOM.value:
            for i in range(num_testpoints):
                testpoint = TestPoint(
                    channel_id = self.id,
                    injection_value = injection_value_list[i],
                    test_value = test_value_list[i]
                )
                self.testpoints.append(testpoint)
                num_added +=1
        
        # Builds a default list of testpoints with an equal distance between the points
        elif testpoint_list_type == TestPointListType.STANDARD.value:            

            # Calculates the nominal signal injection values
            injection_range = self.injection_range()
            delta = injection_range / (num_testpoints - 1)
            injection_values = [self.min_injection_range]
            for i in range(1, num_testpoints):
                injection_values.append(injection_values[i-1] + delta)

            # Calculates the nominal test values for the channel's measurement points
            measurement_range = self.measurement_range()
            delta = measurement_range / (num_testpoints - 1)
            test_values = [self.min_range]
            for i in range(1, num_testpoints):
                test_values.append(test_values[i-1] + delta)

            # Generate each TestPoint and add them to the channel
            for i in range(num_testpoints):
                testpoint = TestPoint(
                    channel_id = self.id,
                    nominal_injection_value = injection_values[i],
                    nominal_test_value = test_values[i]
                )
                self.testpoints.append(testpoint)
                num_added += 1
        
        num_leftover = num_testpoints - num_added
        if num_leftover > 0:
            print(f'Error building TestPoint value list. Only {num_testpoints - num_leftover}/{num_testpoints} added successfully.')
            print(f'TestPointListType = {testpoint_list_type}')
            print(f'InjectionValueList = {injection_value_list}')
            print(f'TestValueList = {test_value_list}')
            print(f'NumTestPoints = {num_testpoints}')
        else:
            print(f'Successfully built TestPoint list with {num_testpoints} TestPoints.')

    def testpoint_stats(self):

        # Statistics tracking variables
        num_untested = 0
        num_passed = 0
        num_failed = 0

        # Tally up the results
        for testpoint in self.testpoints:

            test_result = testpoint.test_result

            if test_result == TestResult.UNTESTED.value:
                num_untested += 1
            elif test_result == TestResult.PASS.value:
                num_passed += 1
            elif test_result == TestResult.FAIL.value:
                num_failed += 1
        
        # Compile and return the results
        return {
            TestResult.UNTESTED.value: num_untested,
            TestResult.PASS.value: num_passed,
            TestResult.FAIL.value: num_failed
        }

    def update_status(self):

        # Unpack the stats
        stats = self.testpoint_stats()
        num_testpoints = self.num_testpoints()
        
        # Determine the new status
        if num_testpoints == stats[TestResult.UNTESTED.value]:
            self.status = TestResult.UNTESTED.value

        elif num_testpoints == stats[TestResult.PASS.value]:
            self.status = TestResult.PASS.value

        elif stats[TestResult.FAIL.value] > 0:
            self.status = TestResult.FAIL.value

        else:
            self.status = Status.IN_PROGRESS.value

        # Save the results
        db.session.commit()

    def testpoint_progress(self):

        # Get the testpoint stats
        stats = self.testpoint_stats()
        num_testpoints = self.num_testpoints()

        # Calculate and return the progress bar percentages
        return {
            "percent_untested": calc_percent(stats[TestResult.UNTESTED.value], num_testpoints),
            "percent_passed": calc_percent(stats[TestResult.PASS.value], num_testpoints),
            "percent_failed": calc_percent(stats[TestResult.FAIL.value], num_testpoints),
        }

    def add_test_equipment_type(self, test_equipment_type):
        self.required_test_equipment.append(test_equipment_type)

    def add_test_equipment(self, test_equipment):
        self.test_equipment.append(test_equipment)        


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(16), default=Status.NOT_STARTED.value)

    # Foreign Keys
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))

    # Relationships
    channels = db.relationship('Channel', backref='group', lazy='dynamic')

    def __repr__(self):
        return f'<Group {self.name}>'

    def job(self):
        return Job.query.filter_by(id=self.job_id).first()

    def num_channels(self):
        return len(self.channels.all())

    def channel_stats(self):

        # Return the analyzed list of all the channels in the Group
        return channel_stats(self.channels.all())

    def update_status(self):

        # Unpack the stats
        stats = self.channel_stats()
        num_channels = self.num_channels()

        # Determine the new status
        if num_channels == stats[TestResult.UNTESTED.value]:
            self.status = Status.NOT_STARTED.value

        elif num_channels == stats[TestResult.PASS.value]:
            self.status = Status.COMPLETE.value

        else:
            self.status = Status.IN_PROGRESS.value
        
        db.session.commit()

    def channel_progress(self):

        # Returns the channel's progress bar width percentages
        return channel_progress(self)
        
        
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stage = db.Column(db.String(16))
    phase = db.Column(db.String(8))
    status = db.Column(db.String(16), default=Status.NOT_STARTED.value)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign Keys
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

    # Relationships
    groups = db.relationship('Group', backref='job', lazy='dynamic')

    def __repr__(self):
        return f'<Job: {self.stage} {self.phase} for the {self.project.name} project>'

    def project(self):
        return Project.query.filter_by(id=self.project_id).first()

    def channels(self):

        # List of all the job's channels
        channels = []
        
        for group in self.groups.all():
            # Add the group's list of channels to the job's list of channels
            channels += group.channels.all()
        
        return channels

    def num_channels(self):
        return len(self.channels())

    def channel_stats(self):

        # Return the analyzed list of all the channels in the Job
        return channel_stats(self.channels())

    def update_status(self):

        # Unpack the status
        stats = self.channel_stats()
        num_channels = self.num_channels()

        # Determine the new status
        if num_channels == stats[TestResult.UNTESTED.value]:
            self.status = Status.NOT_STARTED.value

        elif num_channels == stats[TestResult.PASS.value]:
            self.status = Status.COMPLETE.value

        else:
            self.status = Status.IN_PROGRESS.value

        # Save the changes
        db.session.commit()

    def channel_progress(self):

        # Returns the channel's progress bar width percentages
        return channel_progress(self)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    number = db.Column(db.Integer)
    status = db.Column(db.String(16), default=Status.NOT_STARTED.value)

    # Foreign Keys
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))

    # Relationships
    jobs = db.relationship('Job', backref='project', lazy='dynamic')
    members = db.relationship('User', secondary=project_members, backref='projects',
        lazy='dynamic')
    test_equipment = db.relationship('TestEquipment', secondary=project_equipment,
        backref='projects', lazy='dynamic')

    def __repr__(self):
        return f'<Project {self.number}: {self.name}>'

    def client(self):
        return Client.query.filter_by(id=self.client_id).first()

    def channels(self):

        # List of all the projects channels
        channels = []

        for job in self.jobs.all():
            # Add the jobs's list of channels to the projects's list of channels
            channels += job.channels()
        
        return channels

    def num_channels(self):
        return len(self.channels())

    def channel_stats(self):

        # Return the analyszed list of all the channels in the Project
        return channel_stats(self.channels())

    def update_status(self):

        # Unpack the status
        stats = self.channel_stats()
        num_channels = self.num_channels()

        # Determine the new status
        if num_channels == stats[TestResult.UNTESTED.value]:
            self.status = Status.NOT_STARTED.value

        elif num_channels == stats[TestResult.PASS.value]:
            self.status = Status.COMPLETE.value

        else:
            self.status = Status.IN_PROGRESS.value

        # Save the changes
        db.session.commit()

    def channel_progress(self):

        # Returns the channel's progress bar width percentages
        return channel_progress(self)

    def has_member(self, user):
        return self.members.filter(project_members.c.user_id == user.id).count() > 0

    def add_member(self, user):
        if not self.has_member(user):
            self.members.append(user)

    def remove_member(self, user):
        if self.has_member(user):
            self.members.remove(user)  

    def has_test_equipment(self, test_equipment):
        return self.test_equipment.filter_by(id=test_equipment.id).count() > 0

    def add_test_equipment(self, test_equipment):
        if not self.has_test_equipment(test_equipment):
            self.test_equipment.append(test_equipment)

    def remove_test_equipment(self, test_equipment):
        if self.has_test_equipment(test_equipment):
            self.test_equipment.remove(test_equipment)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))

    # Relationships
    projects = db.relationship('Project', backref='client', lazy='dynamic')

    def __repr__(self):
        return f'<Client: {self.name}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)


    def __repr__(self):
        return f'<User {self.username}: {self.email}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        # Generate a string with hexidecimal digits using the user's email
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=retro&s={size}'

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256'
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    '''
    Project Relationship:
    - Use the backref in the Project.members relationship to get the list of projects
    that belongs to a single User
    ex. user.projects returns [u1, u2]
    '''


# Keeps track of the logged in user by storing it Flask's user session
@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class TestEquipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(24))
    name = db.Column(db.String(32))
    manufacturer = db.Column(db.String(24))
    model_num = db.Column(db.String(24))
    serial_num = db.Column(db.Integer)

    # Foreign Keys
    test_equipment_type_id = db.Column(db.Integer, db.ForeignKey('test_equipment_type.id'))

    # Relationships
    calibration_records = db.relationship('CalibrationRecord', backref='test_equipment', lazy='dynamic')
    channels = db.relationship('ChannelEquipmentRecord', back_populates='test_equipment')
    
    def __repr__(self):
	    return f'<TestEquipment {self.asset_id}: {self.manufacturer} {self.name}>'

    def add_calibration_record(self, calibration_record):
        self.calibration_records.append(calibration_record)

    def remove_calibration_record(self, calibration_record):
        self.calibration_records.append(calibration_record)

    def due_date(self):
        # Get the most recent calibration record
        latest_record = self.calibration_records.filter_by(test_equipment_id=self.id) \
            .order_by(CalibrationRecord.calibration_due_date.desc()).first()
        
        if latest_record is None:
            return None
        else:
            return latest_record.calibration_due_date


class TestEquipmentType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))

    # Relationships
    test_equipment = db.relationship('TestEquipment', backref='test_equipment_type',
        lazy='dynamic')

    def __repr__(self):
        return f'<TestEquipmentType {self.id}: {self.name}>'

    def has_test_equipment(self, test_equipment):
        return self.test_equipment.filter_by(id=test_equipment.id).count() > 0

    def add_test_equipment(self, test_equipment):
        if not self.has_test_equipment(test_equipment):
            self.test_equipment.append(test_equipment)

    def remove_test_equipment(self, test_equipment):
        if self.has_test_equipment(test_equipment):
            self.test_equipment.remove(test_equipment)    


class CalibrationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    calibration_date = db.Column(db.DateTime)
    calibration_due_date = db.Column(db.DateTime)

    # Foreign Keys
    test_equipment_id = db.Column(db.Integer, db.ForeignKey('test_equipment.id'))

    def __repr__(self):
        test_equipment = self.get_test_equipment()
        return f'CalibrationRecord for {test_equipment.name} ({test_equipment.asset_id}) due {self.calibration_due_date}'

    def get_test_equipment(self):
        return TestEquipment.query.filter_by(id=self.test_equipment_id).first()

# Stores a record of the TestEquipment used on a channel when tested for comparing calibration due dates to the test date 
# Ex. Channel id-4 was tested with DMM id-1 at '16:03 July 2, 2021' where DMM id-1 is due for calibration on 00:00 Nov 12, 2021
class ChannelEquipmentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    test_equipment_id = db.Column(db.Integer, db.ForeignKey('test_equipment.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    calibration_due_date = db.Column(db.DateTime)

    # Relationships
    channel = db.relationship('Channel', back_populates='test_equipment')
    test_equipment = db.relationship('TestEquipment', back_populates='channels')
