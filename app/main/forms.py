from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField, HiddenField
from wtforms.fields.core import FieldList, FloatField, FormField
from wtforms.fields.simple import TextAreaField
from wtforms.fields.html5 import DateField
from wtforms.validators import ValidationError, DataRequired
from app.models import User, Client, Project
from app.utils import JobStage, JobPhase, MeasurementType, EngUnits, ErrorType
from app.utils import StandardTestEquipmentTypes, TestPointListType

# FormField class constants
CUSTOM_SELECT_CLASS = {'class': 'custom-select'}
CUSTOM_FORM_CLASS = {'class': 'form-control'}
PRIMARY_SUBMIT_BUTTON_CLASS = {'class': 'btn btn-primary'}

# SelectField choice constants
EMPTY_SELECT_CHOICE = [("", 'Select...')]
JOB_PHASE_CHOICES = EMPTY_SELECT_CHOICE + [(phase.value, phase.value) for phase in JobPhase]
JOB_STAGE_CHOICES = EMPTY_SELECT_CHOICE + [(stage.value, stage.value) for stage in JobStage]
MEASUREMENT_TYPE_CHOICES = EMPTY_SELECT_CHOICE + [(t.value, t.value) for t in MeasurementType]
ENG_UNITS_CHOICES = EMPTY_SELECT_CHOICE + [(units.value, units.value) for units in EngUnits]
ERROR_TYPE_CHOICES = EMPTY_SELECT_CHOICE + [(e.value, e.value) for e in ErrorType]
NUM_TESTPOINT_CHOICES = [(i, i) for i in range(1, 11)]
TESTPOINT_LIST_TYPE_CHOICES = [(t.value, t.value) for t in TestPointListType]
TEST_EQUIPMENT_TYPE_CHOICES = EMPTY_SELECT_CHOICE + [(t.value, t.value) for t in StandardTestEquipmentTypes]


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)

        # Get the original username as the form is created
        self.original_username = original_username

    # Customer validator method to ensure the new username is unique
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')


class AddClientForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    submit = SubmitField('Add Client')

    # Custom validator for ensuring a unique client name is chosen
    def validate_name(self, name):
        name = Client.query.filter_by(name=name.data).first()
        if name is not None:
            raise ValidationError('Client name already exists. Please choose another.')


class AddProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired()])
    number = IntegerField('Project Number', validators=[DataRequired()])
    client = SelectField('Client', render_kw=CUSTOM_SELECT_CLASS, validators=[DataRequired()])
    submit = SubmitField('Add Project')

    # Custom validator for ensuring a unique project number is chosen
    def validate_number(self, number):
        number = Project.query.filter_by(number=number.data).first()
        if number is not None:
            raise ValidationError('Project number already exists. Please choose another.')


class AddJobForm(FlaskForm):
    client_name = SelectField('Client Name', render_kw=CUSTOM_SELECT_CLASS, validators=[DataRequired()])
    project_number = SelectField('Project Number', render_kw=CUSTOM_SELECT_CLASS, validators=[DataRequired()])
    project_name = SelectField('Project Name', render_kw=CUSTOM_SELECT_CLASS, validators=[DataRequired()])
    stage = SelectField('Project Stage', choices=JOB_STAGE_CHOICES, render_kw=CUSTOM_SELECT_CLASS, validators=[DataRequired()])
    phase = SelectField('Project Phase', choices=JOB_PHASE_CHOICES, render_kw=CUSTOM_SELECT_CLASS, validators=[DataRequired()])
    submit = SubmitField('Add Job')


class AddGroupForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    job_id = HiddenField('Job ID')
    submit = SubmitField('Add New Group')


class AddTestPointForm(FlaskForm):
    injection_value = FloatField('Injection Value', render_kw=CUSTOM_FORM_CLASS)
    test_value = FloatField('Test Value', render_kw=CUSTOM_FORM_CLASS)


class AddChannelForm(FlaskForm):
    # Basic Channel Info
    name = StringField('Name', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    group_id = HiddenField('Group ID')

    # Measurement Info
    measurement_type = SelectField('Type', render_kw=CUSTOM_SELECT_CLASS,
        choices=MEASUREMENT_TYPE_CHOICES, validators=[DataRequired()])
    measurement_units = SelectField('Engineering Units', render_kw=CUSTOM_SELECT_CLASS,
        choices=ENG_UNITS_CHOICES, validators=[DataRequired()])
    min_range = FloatField('Minimum Range', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    max_range = FloatField('Maximum Range', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    full_scale_range = FloatField('Full Scale Range', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])

    # Tolerance Info
    max_error = FloatField('Maximum Error', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    error_type = SelectField('Error Type', render_kw=CUSTOM_SELECT_CLASS,
        choices=ERROR_TYPE_CHOICES, validators=[DataRequired()])

    # Signal Injection Info
    min_injection_range = FloatField('Minimum Range', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    max_injection_range = FloatField('Maximum Range', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    injection_units = SelectField('Engineering Units', render_kw=CUSTOM_SELECT_CLASS,
        choices=ENG_UNITS_CHOICES, validators=[DataRequired()])

    # Testpoint List Info
    num_testpoints = SelectField('Number of TestPoints', render_kw=CUSTOM_SELECT_CLASS,
        choices=NUM_TESTPOINT_CHOICES, validators=[DataRequired()])
    testpoint_list_type = SelectField('TestPoint List Type', render_kw=CUSTOM_SELECT_CLASS,
        choices=TESTPOINT_LIST_TYPE_CHOICES, validators=[DataRequired()])
    testpoint_list = FieldList(FormField(AddTestPointForm))

    submit = SubmitField('Add Channel', render_kw=PRIMARY_SUBMIT_BUTTON_CLASS)

    # Add a pass for the form to allow for the TestEquipmentType fields to be added before the form is instantiated
    pass


class TestPointForm(FlaskForm):
    injection_value = FloatField('Injection Value', render_kw=CUSTOM_FORM_CLASS)
    test_value = FloatField('Test Value', render_kw=CUSTOM_FORM_CLASS)
    

class ChannelForm(FlaskForm):
    testpoints = FieldList(FormField(TestPointForm))
    interface = StringField('Interface', render_kw=CUSTOM_FORM_CLASS)
    notes = TextAreaField('Notes', render_kw=CUSTOM_FORM_CLASS, default="")


class ChannelsForm(FlaskForm):
    channels = FieldList(FormField(ChannelForm))


class AddTestEquipmentForm(FlaskForm):
    name = SelectField('Name', render_kw=CUSTOM_FORM_CLASS,
        choices=TEST_EQUIPMENT_TYPE_CHOICES, validators=[DataRequired()])
    manufacturer = StringField('Manufacturer', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    model_num = StringField('Model Number', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    serial_num = StringField('Serial Number', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    asset_id = StringField('Asset ID', render_kw=CUSTOM_FORM_CLASS, validators=[DataRequired()])
    calibration_date = DateField('Calibration Date', format='%Y-%m-%d')
    calibration_due_date = DateField('Calibration Due Date', format='%Y-%m-%d')
    submit = SubmitField('Add Test Equipment')


class AddCalibrationRecordForm(FlaskForm):
    calibration_date = DateField('Calibration Date', format='%Y-%m-%d')
    calibration_due_date = DateField('Calibration Due Date', format='%Y-%m-%d')
    submit = SubmitField('Add Calibration Record')


class UpdateProjectMembersForm(FlaskForm):
    submit = SubmitField('Update Members', render_kw=PRIMARY_SUBMIT_BUTTON_CLASS)
    # Lets the form be created dynamically
    pass