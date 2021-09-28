from datetime import datetime
from time import time
from flask import current_app
from flask_login import UserMixin
from app import db, login
from app.utils import *
import jwt, logging, pprint
from hashlib import md5
from werkzeug.security import generate_password_hash, check_password_hash

# Import the logger assigned to the application
logger = logging.getLogger(__name__)

'''Many-to-Many Association Tables'''
# Stores all the Users that have access to a project
project_members = db.Table(
    'project_members', db.Model.metadata,
    db.Column('project_id', db.Integer, db.ForeignKey('project.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

# Stores all the Companies involved in a project
company_projects = db.Table(
    'company_projects', db.Model.metadata,
    db.Column('company_id', db.Integer, db.ForeignKey('company.id')),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id')),
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
        return f'<TestPoint id-{self.id} for Channel>'

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
            if self.measured_test_value == None:
                return self.nominal_test_value * (max_error / 100)
            else:
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
    name = db.Column(db.String(64))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Measurement Info
    measurement_type = db.Column(db.String(32))
    measurement_units = db.Column(db.String(32))
    min_range = db.Column(db.Float(16))
    max_range = db.Column(db.Float(16))
    full_scale_range = db.Column(db.Float(16))

    # Tolerance Info
    max_error = db.Column(db.Float(8))
    error_type = db.Column(db.String(16))

    # Signal Injection Info
    min_injection_range = db.Column(db.Float(16))
    max_injection_range = db.Column(db.Float(16))
    injection_units = db.Column(db.String(32))

    # Metrics
    status = db.Column(db.String(32), default=TestResult.UNTESTED.value)

    # Summary Info
    interface = db.Column(db.String(32))
    notes = db.Column(db.String(128))

    # Group Relationship
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    group = db.relationship('Group', back_populates='channels')

    # Other Relationships
    testpoints = db.relationship('TestPoint', back_populates='channel', lazy='dynamic')
    equipment_records = db.relationship('ChannelEquipmentRecord', back_populates='channel', lazy='dynamic')
    required_test_equipment = db.relationship('TestEquipmentType', secondary=channel_required_equipment, back_populates='channels', lazy='dynamic')

    # Approval Fields
    required_supplier_approval = db.Column(db.Boolean)
    required_client_approval = db.Column(db.Boolean)
    approval_records = db.relationship('ApprovalRecord', back_populates='channel', lazy='dynamic')

    def __repr__(self):
        return f'<Channel {self.name}>'

    def delete_all_records(self):

        for testpoint in self.testpoints.all():
            self.testpoints.remove(testpoint)
        
        for equipment_record in self.equipment_records.all():
            self.equipment_records.remove(equipment_record)

        for test_equipment_type in self.required_test_equipment.all():
            self.required_test_equipment.remove(test_equipment_type)

        for approval_record in self.approval_records.all():
            self.approval_records.remove(approval_record)

    def num_testpoints(self):
        return len(self.testpoints.all())

    def measurement_range(self):
        return self.max_range - self.min_range

    def injection_range(self):
        return self.max_injection_range - self.min_injection_range

    def has_testpoint(self, testpoint):
        return testpoint in self.testpoints

    def add_testpoint(self, testpoint):
        self.testpoints.append(testpoint)

    def remove_testpoint(self, testpoint):
        if self.has_testpoint(testpoint):
            self.testpoints.remove(testpoint)

    def build_testpoint_list(self, num_testpoints, testpoint_list_type, injection_value_list, test_value_list):
        
        # Debugging variables
        num_added = 0

        # Builds a list of custom testpoints defined by the user when a new channel is created
        if testpoint_list_type == TestPointListType.CUSTOM.value:
            for i in range(num_testpoints):
                testpoint = TestPoint(
                    channel_id = self.id,
                    nominal_injection_value = injection_value_list[i],
                    nominal_test_value = test_value_list[i]
                )
                self.testpoints.append(testpoint)
                num_added +=1
        
        # Builds a default list of testpoints with an equal delta between the points
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
                self.add_testpoint(testpoint)
                num_added += 1
        
        num_leftover = num_testpoints - num_added
        if num_leftover > 0:
            logger.error(f'Error building list of TestPoints for Channel ID {self.id}.\n \
                {pprint.pprint([num_testpoints, testpoint_list_type, injection_value_list, test_value_list])}')

    def testpoint_stats(self):

        # Statistics tracking variables
        num_untested = 0
        num_passed = 0
        num_failed = 0

        # Tally up the results
        for testpoint in self.testpoints.all():

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

    def update_each_parent_status(self):
        self.update_status()
        self.group.update_status()
        self.group.job.update_status()
        self.group.job.project.update_status()

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

    def has_test_equipment_type(self, test_equipment_type):
        return test_equipment_type in self.required_test_equipment

    def add_test_equipment_type(self, test_equipment_type):
        if not self.has_test_equipment_type(test_equipment_type):
            self.required_test_equipment.append(test_equipment_type)

    def remove_test_equipment_type(self, test_equipment_type):
        if self.has_test_equipment_type(test_equipment_type):
            self.required_test_equipment.remove(test_equipment_type)

    def current_test_equipment(self, test_equipment_type_id):

        # Get the most recent ChannelEquipmentRecord that has a record of being used on the channel
        record = self.equipment_records.filter_by(test_equipment_type_id=test_equipment_type_id) \
            .order_by(ChannelEquipmentRecord.timestamp.desc()).first()

        return record.test_equipment if record is not None else None

    def update_required_approvals(self):
        job_phase = self.group.job.phase

        # Add a requirement for the Supplier's approval of a channel regardless of the job
        self.required_supplier_approval = True
        
        # Add a requirement for a Client's approval if the job is an ATP
        self.required_client_approval = job_phase == JobPhase.ATP.value

    def has_approval_from_user(self, user):
        return self.approval_records.filter_by(user_id=user.id).count() > 0

    def add_approval(self, user):
        if not self.has_approval_from_user(user):

            # Create a record of the Channel being signed by the User
            record = ApprovalRecord(
                channel_id=self.id,
                user_id=user.id,
                timestamp=datetime.utcnow(),
                company_category=user.company.category
            )
            self.approval_records.append(record)

    def remove_approval(self, user):
        if self.has_approval_from_user(user):

            # Find the existing record to remove
            record = self.approval_records.filter_by(user_id=user.id).first()
            self.approval_records.remove(record)

    def supplier_approval_record(self):
        return self.approval_records.filter_by(company_category=CompanyCategory.SUPPLIER.value).first()

    def client_approval_record(self):
        return self.approval_records.filter_by(company_category=CompanyCategory.CLIENT.value).first()


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
    channels = db.relationship('Channel', back_populates='group', lazy='dynamic')

    def __repr__(self):
        return f'<Group {self.name}>'

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
    __tablename__ = 'job'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    stage = db.Column(db.String(16))
    phase = db.Column(db.String(16))
    status = db.Column(db.String(16), default=Status.NOT_STARTED.value)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Project Relationship
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project', back_populates='jobs')

    # Group Relationship
    groups = db.relationship('Group', back_populates='job', lazy='dynamic')

    def __repr__(self):
        return f'<Job: {self.stage} {self.phase} for the {self.project.name} project>'

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
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    number = db.Column(db.Integer)
    status = db.Column(db.String(16), default=Status.NOT_STARTED.value)

    # Relationships
    jobs = db.relationship('Job', back_populates='project', lazy='dynamic')
    members = db.relationship('User', secondary=project_members, back_populates='projects', lazy='dynamic')
    test_equipment = db.relationship('TestEquipment', secondary=project_equipment, back_populates='projects', lazy='dynamic')
    companies = db.relationship('Company', secondary=company_projects, back_populates='projects', lazy='dynamic')


    def __repr__(self):
        return f'<Project {self.number}: {self.name}>'

    def has_company(self, company):
        return company in self.companies

    def add_company(self, company):
        if not self.has_company(company):
            self.companies.append(company)

    def remove_company(self, company):
        if self.has_company(company):
            self.companies.remove(company)

    def supplier(self):
        for company in self.companies.order_by('name').all():
            if company.category == CompanyCategory.SUPPLIER.value:
                return company 

        # Return None if no Supplier companies are assigned to the project yet
        return None

    def client(self):
        for company in self.companies.order_by('name').all():
            if company.category == CompanyCategory.CLIENT.value:
                return company 

        # Return None if no Client companies are assigned to the project yet
        return None

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
        return user in self.members

    def add_member(self, user):
        if not self.has_member(user):
            self.members.append(user)

    def add_members(self, users):
        for user in users:
            self.add_member(user)

    def remove_member(self, user):
        if self.has_member(user):
            self.members.remove(user)  

    def remove_members(self, users):
        for user in users:
            self.remove_member(user)

    def has_test_equipment(self, test_equipment):
        return test_equipment in self.test_equipment

    def add_test_equipment(self, test_equipment):
        if not self.has_test_equipment(test_equipment):
            self.test_equipment.append(test_equipment)

    def remove_test_equipment(self, test_equipment):
        if self.has_test_equipment(test_equipment):
            self.test_equipment.remove(test_equipment)
    
    def test_equipment_of_type(self, test_equipment_type):
        return self.test_equipment.filter_by(name=test_equipment_type.name).all()

    def has_test_equipment_of_type(self, test_equipment_type):
        return len(self.test_equipment_of_type(test_equipment_type)) > 0


class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(48))
    category = db.Column(db.String(24))

    # Employee Relationship
    employees = db.relationship('User', back_populates='company', lazy='dynamic')

    # Project Relationship
    projects = db.relationship('Project', secondary=company_projects, back_populates='companies', lazy='dynamic')    

    def __repr__(self):
        return f'<Company ({self.category}): {self.name}>'

    def suppliers():
        suppliers = []
        for company in Company.query.order_by('name').all():
            if company.category == CompanyCategory.SUPPLIER.value:
                suppliers.append(company)
        return suppliers

    def clients():
        clients = []
        for company in Company.query.order_by('name').all():
            if company.category == CompanyCategory.CLIENT.value:
                clients.append(company)
        return clients

    def has_employee(self, user):
        return user in self.employees

    def add_employee(self, user):
        if not self.has_employee(user):
            self.employees.append(user)
    
    def remove_employee(self, user):
        if self.has_employee(user):
            self.employees.remove(user)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    first_name = db.Column(db.String(48))
    last_name = db.Column(db.String(48))
    email = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

    # Company Relationship
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    company = db.relationship('Company', back_populates='employees')

    # Relationships
    projects = db.relationship('Project', secondary=project_members, back_populates='members', lazy='dynamic')
    approval_records = db.relationship('ApprovalRecord', back_populates='user', lazy='dynamic')


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

    def full_name(self):
        return self.first_name + ' ' + self.last_name

    def first_letter_last_name(self):
        return self.first_name[0] + '. ' + self.last_name


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
    serial_num = db.Column(db.String(32))

    # TestEquipmentType Relationship
    test_equipment_type_id = db.Column(db.Integer, db.ForeignKey('test_equipment_type.id'))
    test_equipment_type = db.relationship('TestEquipmentType', back_populates='test_equipment')

    # Other Relationships
    calibration_records = db.relationship('CalibrationRecord', back_populates='test_equipment', lazy='dynamic')
    channel_equipment_records = db.relationship('ChannelEquipmentRecord', back_populates='test_equipment', lazy='dynamic')
    projects = db.relationship('Project', secondary=project_equipment, back_populates='test_equipment', lazy='dynamic')
    
    def __repr__(self):
	    return f'<TestEquipment {self.asset_id}: {self.manufacturer} {self.name}>'

    def has_calibration_record(self, calibration_record):
        return calibration_record in self.calibration_records

    def add_calibration_record(self, calibration_record):
        if not self.has_calibration_record(calibration_record):
            self.calibration_records.append(calibration_record)

    def remove_calibration_record(self, calibration_record):
        if self.has_calibration_record(calibration_record):
            self.calibration_records.remove(calibration_record)

    def due_date(self):
        # Get the most recent calibration record
        return self.calibration_records.order_by(CalibrationRecord.calibration_due_date.desc()).first().calibration_due_date


class TestEquipmentType(db.Model):
    __tablename__ = 'test_equipment_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))

    # TestEquipment Relationship
    test_equipment = db.relationship('TestEquipment', back_populates='test_equipment_type', lazy='dynamic')
    channels = db.relationship('Channel', secondary=channel_required_equipment, back_populates='required_test_equipment', lazy='dynamic')

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
    channel = db.relationship('Channel', back_populates='equipment_records')

    # TestEquipmentType ForeignKey
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
    company_category = db.Column(db.String(16))

    # Channel Relationship
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    channel = db.relationship('Channel', back_populates='approval_records')

    # User Relationship
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='approval_records')

    def __repr__(self):
        return f'<ApprovalRecord for channel id-{self.channel_id} signed by user id-{self.user_id} at {self.timestamp}>'    

