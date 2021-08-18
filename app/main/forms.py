from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField
from wtforms.validators import ValidationError, DataRequired
from app.models import User, Client, Project

# Constants
CUSTOM_SELECT_FIELD_KW = {'class': 'custom-select'}

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
    client = SelectField('Client', render_kw=CUSTOM_SELECT_FIELD_KW, validators=[DataRequired()])
    submit = SubmitField('Add Project')

    # Custom validator for ensuring a unique project number is chosen
    def validate_number(self, number):
        number = Project.query.filter_by(number=number.data).first()
        if number is not None:
            raise ValidationError('Project number already exists. Please choose another.')