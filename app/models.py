from datetime import datetime
from time import time
from flask import current_app
from flask_login import UserMixin
from app import db, login
from app.utils import *
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
    __tablename__ = 'testpoint'
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

    # Channel Relationship
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    channel = db.relationship('Channel', back_populates='testpoints')

    def __repr__(self):
        return f'<TestPoint id-{self.id} for Channel {self.channel.name}>'

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
    __tablename__ = 'channel'
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

    # Group Relationship
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    group = db.relationship('Group', back_populates='channels')

    # Other Relationships
    testpoints = db.relationship('TestPoint', back_populates='channel')
    test_equipment = db.relationship('ChannelEquipmentRecord', back_populates='channel')
    required_test_equipment = db.relationship('TestEquipmentType', secondary=channel_required_equipment, back_populates='channels')
    approvals = db.relationship('ApprovalRecord', back_populates='channel')

    def __repr__(self):
        return f'<Channel {self.name}>'

    def num_testpoints(self):
        return len(self.testpoints)

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

    def current_test_equipment(self, test_equipment_type_id):

        # Sorting criteria to sort by timestamp of a ChannelEquipmentRecord
        def sort_by_datetime(channel_equipment_record):
            return channel_equipment_record.timestamp

        # Return the TestEquipment that is used on the latest record for a channel
        records = self.test_equipment

        # Return None if the channel has no history of TestEquipment assigned to it
        if len(records) == 0:
            return None

        # Starting at the most recent record, check through all the records for the specified TestEquipmentType
        records.sort(reverse=True, key=sort_by_datetime)
        for record in records:
            if record.test_equipment_type_id == test_equipment_type_id:
                return TestEquipment.query.filter_by(id=record.test_equipment_id).first()

        # If no record is found, then return None
        return None

    def has_approval_from_user(self, user):
        return self.approvals.filter(user_id=user.id).count() > 0

    def add_approval(self, user):
        if not self.has_approval_from_user(user):

            # Create a record of the Channel being signed by the User
            record = ApprovalRecord(
                channel_id=self.id,
                user_id=user.id,
                timestamp=datetime.utcnow()
            )
            self.approvals.append(record)

    def remove_approval(self, user):
        if self.has_approval_from_user(user):

            # Find the existing record to remove
            record = self.approvals.filter_by(user_id=user.id).first()
            self.approvals.remove(record)


class Group(db.Model):
    __tablename__ = 'group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(16), default=Status.NOT_STARTED.value)

    # Job Relationship
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    job = db.relationship('Job', back_populates='groups')

    # Channel Relationship
    channels = db.relationship('Channel', back_populates='group')

    def __repr__(self):
        return f'<Group {self.name}>'

    def num_channels(self):
        return len(self.channels)

    def channel_stats(self):

        # Return the analyzed list of all the channels in the Group
        return channel_stats(self.channels)

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
    __tablename__ = 'job'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    stage = db.Column(db.String(16))
    phase = db.Column(db.String(8))
    status = db.Column(db.String(16), default=Status.NOT_STARTED.value)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Project Relationship
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project', back_populates='jobs')

    # Group Relationship
    groups = db.relationship('Group', back_populates='job')

    def __repr__(self):
        return f'<Job: {self.stage} {self.phase} for the {self.project.name} project>'

    def channels(self):

        # List of all the job's channels
        channels = []
        
        for group in self.groups:
            # Add the group's list of channels to the job's list of channels
            channels += group.channels
        
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
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    number = db.Column(db.Integer)
    status = db.Column(db.String(16), default=Status.NOT_STARTED.value)

    # Relationships
    jobs = db.relationship('Job', back_populates='project')
    members = db.relationship('User', secondary=project_members, back_populates='projects')
    test_equipment = db.relationship('TestEquipment', secondary=project_equipment, back_populates='projects')
    
    # Client reference
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    client = db.relationship('Client', back_populates='projects')

    # Supplier reference
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    supplier = db.relationship('Supplier', back_populates='projects')

    def __repr__(self):
        return f'<Project {self.number}: {self.name}>'

    def channels(self):

        # List of all the projects channels
        channels = []

        for job in self.jobs:
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
        return user in self.members

    def add_member(self, user):
        if not self.has_member(user):
            self.members.append(user)

    def remove_member(self, user):
        if self.has_member(user):
            self.members.remove(user)  

    def has_test_equipment(self, test_equipment):
        return test_equipment in self.test_equipment

    def add_test_equipment(self, test_equipment):
        if not self.has_test_equipment(test_equipment):
            self.test_equipment.append(test_equipment)

    def remove_test_equipment(self, test_equipment):
        if self.has_test_equipment(test_equipment):
            self.test_equipment.remove(test_equipment)
    
    def test_equipment_of_type(self, test_equipment_type):

        # Get a list of all the TestEquipment on the project
        all_project_test_equipment = self.test_equipment
        test_equipment_list = []

        # Filter the list to be only TestEquipment with the same TestEquipmentType specified
        for test_equipment in all_project_test_equipment:
            if test_equipment.name == test_equipment_type.name:
                test_equipment_list.append(test_equipment)
        
        return test_equipment_list


class Supplier(db.Model):
    __tablename__ = 'supplier'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(48))

    # Project Relationship
    projects = db.relationship('Project', back_populates='supplier')

    def __repr__(self):
        return f'<Supplier: {self.name}>'


class Client(db.Model):
    __tablename__ = 'client'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(48))

    # Project Relationship
    projects = db.relationship('Project', back_populates='client')

    def __repr__(self):
        return f'<Client: {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

    # Relationships
    approval_records = db.relationship('ApprovalRecord', back_populates='user')
    projects = db.relationship('Project', secondary=project_members, back_populates='members')

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


# Keeps track of the logged in user by storing it Flask's user session
@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class TestEquipment(db.Model):
    __tablename__ = 'test_equipment'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(24))
    name = db.Column(db.String(32))
    manufacturer = db.Column(db.String(24))
    model_num = db.Column(db.String(24))
    serial_num = db.Column(db.Integer)

    # TestEquipmentType Relationship
    test_equipment_type_id = db.Column(db.Integer, db.ForeignKey('test_equipment_type.id'))
    test_equipment_type = db.relationship('TestEquipmentType', back_populates='test_equipment')

    # Other Relationships
    calibration_records = db.relationship('CalibrationRecord', back_populates='test_equipment')
    channel_equipment_records = db.relationship('ChannelEquipmentRecord', back_populates='test_equipment')
    projects = db.relationship('Project', secondary=project_equipment, back_populates='test_equipment')
    
    def __repr__(self):
	    return f'<TestEquipment {self.asset_id}: {self.manufacturer} {self.name}>'

    def add_calibration_record(self, calibration_record):
        self.calibration_records.append(calibration_record)

    def remove_calibration_record(self, calibration_record):
        self.calibration_records.append(calibration_record)

    def due_date(self):
        # Get the most recent calibration record
        latest_record = CalibrationRecord.query.filter_by(test_equipment_id=self.id) \
            .order_by(CalibrationRecord.calibration_due_date.desc()).first()
        
        if latest_record is None:
            return None
        else:
            return latest_record.calibration_due_date


class TestEquipmentType(db.Model):
    __tablename__ = 'test_equipment_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))

    # TestEquipment Relationship
    test_equipment = db.relationship('TestEquipment', back_populates='test_equipment_type')
    channels = db.relationship('Channel', secondary=channel_required_equipment, back_populates='required_test_equipment')

    def __repr__(self):
        return f'<TestEquipmentType {self.id}: {self.name}>'

    def has_test_equipment(self, test_equipment):
        return test_equipment in self.test_equipment

    def add_test_equipment(self, test_equipment):
        if not self.has_test_equipment(test_equipment):
            self.test_equipment.append(test_equipment)

    def remove_test_equipment(self, test_equipment):
        if self.has_test_equipment(test_equipment):
            self.test_equipment.remove(test_equipment)    


class CalibrationRecord(db.Model):
    __tablename__ = 'calibration_record'
    id = db.Column(db.Integer, primary_key=True)
    calibration_date = db.Column(db.DateTime)
    calibration_due_date = db.Column(db.DateTime)

    # Test Equipment Relationship
    test_equipment_id = db.Column(db.Integer, db.ForeignKey('test_equipment.id'))
    test_equipment = db.relationship('TestEquipment', back_populates='calibration_records')

    def __repr__(self):
        test_equipment = self.test_equipment
        return f'<CalibrationRecord for {test_equipment.name} ({test_equipment.asset_id}) due {self.calibration_due_date}>'


# Stores a record of the TestEquipment used on a channel when tested for comparing calibration due dates to the test date 
# Ex. Channel id-4 was tested with DMM id-1 at '16:03 July 2, 2021' where DMM id-1 is due for calibration on 00:00 Nov 12, 2021
class ChannelEquipmentRecord(db.Model):
    __tablename__ = 'channel_equipment_record'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    calibration_due_date = db.Column(db.DateTime)

    # Channel Relationship
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    channel = db.relationship('Channel', back_populates='test_equipment')

    # TestEquipmentType Relationship
    test_equipment_type_id = db.Column(db.Integer, db.ForeignKey('test_equipment_type.id'))

    # TestEquipment Relationship
    test_equipment_id = db.Column(db.Integer, db.ForeignKey('test_equipment.id'))
    test_equipment = db.relationship('TestEquipment', back_populates='channel_equipment_records')

    def __repr__(self):
        return f'<ChannelEquipmentRecord for channel id-{self.channel_id} and {self.test_equipment.name} ({self.test_equipment.asset_id}) at {self.timestamp}>'


class ApprovalRecord(db.Model):
    __tablename__ = 'approval_record'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Channel Relationship
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    channel = db.relationship('Channel', back_populates='approvals')

    # User Relationship
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='approval_records')

    def __repr__(self):
        return f'<ApprovalRecord for channel id-{self.channel_id} signed by user id-{self.user_id} at {self.timestamp}>'    
