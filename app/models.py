from datetime import datetime
from time import time
from flask import current_app
from flask_login import UserMixin
from app import db, login
from app.utils import ErrorType, TestPointListType
import jwt
from hashlib import md5
from werkzeug.security import generate_password_hash, check_password_hash


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
    test_result = db.Column(db.String(12))
    notes = db.Column(db.String(128))

    # Foreign Keys
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))

    def __repr__(self):
        return f'<TestPoint {self.id} for Channel {self.channel().name}>'


    def channel(self):
        return Channel.query.filter_by(id=self.channel_id).first()


    # Calculates the measured error from a signal injection
    def calc_error(self):
        return self.nominal_test_value - self.measured_test_value


    # Calculates the maximum error for a measurement based on the error type
    def calc_max_error(self):
        channel = self.channel()
        error_type = channel.error_type
        max_error = channel.max_error

        # Returns an error in the engineering units provided
        # ex. max_error = +/- 0.05 VDC
        if error_type == ErrorType.ENG_UNITS:
            return max_error

        # Returns an error calculated from the channel's full scale range
        # ex. max_error of 0.05 %FS is equivalent to 0.125 psi on a 0-250 psi full scale range
        elif error_type == ErrorType.PERCENT_FULL_SCALE:
            return channel.full_scale_range * (max_error / 100)

        # Returns an error based on the measured/read value being evaluated
        # ex. max_error of 0.1 %RDG is equivalent to 0.015 Hz at a measured value of 15 Hz
        elif error_type == ErrorType.PERCENT_READING:
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

    # Foreign Keys
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    # Relationships
    testpoints = db.relationship('TestPoint', backref='channel', lazy='dynamic')

    def __repr__(self):
        return f'<Channel {self.name}>'

    def group(self):
        return Group.query.filter_by(id=self.group_id).first()

    def num_testpoints(self):
        return len(self.testpoints)

    def measurement_range(self):
        return self.max_range - self.min_range

    def injection_range(self):
        return self.max_injection_range - self.min_injection_range

    def build_testpoint_list(self, num_testpoints, testpoint_list_type, nominal_injection_value_list, nominal_test_value_list):
        
        # Checker variables
        num_added = 0

        # Builds a list of testpoints defined by the user when a new channel is created
        if testpoint_list_type == TestPointListType.CUSTOM:
            for i in range(num_testpoints):
                testpoint = TestPoint(
                    channel_id = self.id,
                    nominal_injection_value = nominal_injection_value_list[i],
                    nominal_test_value = nominal_test_value_list[i]
                )
                self.testpoints.append(testpoint)
                num_added +=1
        
        # Builds a default list of testpoints with an equal distance between the points
        elif testpoint_list_type == TestPointListType.STANDARD:

            # Calculates the nominal signal injection values
            injection_range = self.injection_range()
            delta = injection_range / (num_testpoints - 1)
            nominal_injection_values = [self.min_injection_range]
            for i in range(1, num_testpoints):
                nominal_injection_values.append(nominal_injection_value_list[i-1] + delta)

            # Calculates the nominal test values for the channel's measurement points
            measurement_range = self.measurement_range()
            delta = measurement_range / (num_testpoints - 1)
            nominal_test_values = [self.min_range]
            for i in range(1, num_testpoints):
                nominal_test_values.append(nominal_test_value_list[i-1] + delta)

            # Generate each TestPoint and add them to the channel
            for i in range(num_testpoints):
                testpoint = TestPoint(
                    channel_id = self.id,
                    nominal_injection_value = nominal_injection_values[i],
                    nominal_test_value = nominal_test_values[i]
                )
                self.testpoints.append(testpoint)
                num_added += 1
        
        num_leftover = num_testpoints - num_added
        if num_leftover > 0:
            print(f'Error building TestPoint value list. Only {num_testpoints - num_leftover}/{num_testpoints} added successfully.')
        else:
            print(f'Successfully built TestPoint value list with {num_testpoints} points.')


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign Keys
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))

    # Relationships
    channels = db.relationship('Channel', backref='group', lazy='dynamic')

    def __repr__(self):
        return f'<Group {self.name}>'

    def job(self):
        return Job.query.filter_by(id=self.job_id).first()


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stage = db.Column(db.String(16))
    phase = db.Column(db.String(8))    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign Keys
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

    # Relationships
    groups = db.relationship('Group', backref='job', lazy='dynamic')


    def __repr__(self):
        return f'<Job: {self.stage} {self.phase} for the {self.project.name} project>'

    def project(self):
        return Project.query.filter_by(id=self.project_id).first()


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    number = db.Column(db.Integer)

    # Foreign Keys
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))

    # Relationships
    jobs = db.relationship('Job', backref='project', lazy='dynamic')

    def __repr__(self):
        return f'<Project {self.number}: {self.name}>'

    def client(self):
        return Client.query.filter_by(id=self.client_id).first()


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


# Keeps track of the logged in user by storing it Flask's user session
@login.user_loader
def load_user(id):
    return User.query.get(int(id))
