from flask import render_template, url_for, request, current_app, redirect, flash, jsonify
from flask_login import current_user, login_required
from datetime import datetime
from app import db
from app.main import bp
from app.models import TestPoint, User, Client, Project, Job, Group, Channel
from app.main.forms import EditProfileForm, AddClientForm, AddProjectForm, AddJobForm, AddGroupForm, AddChannelForm
from app.main.forms import ChannelsForm, ChannelForm, TestPointForm
from app.main.forms import EMPTY_SELECT_CHOICE
from app.utils import TestPointListType, none_if_empty

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():

    summary = {}

    users = User.query.all()
    summary["users"] = users

    clients = Client.query.all()
    summary["clients"] = clients

    projects = Project.query.all()
    summary["projects"] = projects

    jobs = Job.query.all()
    summary["jobs"] = jobs

    groups = Group.query.all()
    summary["groups"] = groups

    channels = Channel.query.all()
    summary["channels"] = channels

    return render_template('index.html', title='Home', summary=summary)


@bp.route('/user/<username>')
@login_required
def user(username):

    # Get the profile of the current_user
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():

    form = EditProfileForm(current_user.username)

    # User has changed their profile information
    if form.validate_on_submit():

        # Update the database with the user's changes to their profile information
        current_user.username = form.username.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))

    # User is only visiting their profile
    elif request.method == 'GET':
        form.username.data = current_user.username

    return render_template('edit_profile.html', title='Edit Profile', form=form)


@bp.route('/add_client', methods=['GET', 'POST'])
@login_required
def add_client():

    # Create the form
    form = AddClientForm()

    # User has added a new client
    if form.validate_on_submit():

        # Add the new client to the database
        client = Client(name=form.name.data)
        db.session.add(client)
        db.session.commit()
        flash(f'Client "{client.name}" has been added to the database.')
        return redirect(url_for('main.index'))

    return render_template('add_item.html', title='Add Client', form=form, item='Client')


@bp.route('/add_project', methods=['GET', 'POST'])
def add_project():

    # Create the form
    form = AddProjectForm()

    # Generate the list of SelectField choices to populate in the form
    form.client.choices = EMPTY_SELECT_CHOICE + [(c.id, c.name) for c in Client.query.order_by('name')]

    # User has added a new project
    if form.validate_on_submit():

        # Add the new project to the database
        project = Project(
            name=form.name.data,
            number=form.number.data,
            client_id=form.client.data
            )
        db.session.add(project)
        db.session.commit()
        flash(f'Project "{project.name}" has been added to the database.')
        return redirect(url_for('main.index'))

    return render_template('add_item.html', title='Add Project', form=form, item='Project')


@bp.route('/projects', methods=['GET', 'POST'])
def projects():

    projects = Project.query.all()

    return render_template('projects.html', title='Projects List', projects=projects)


@bp.route('/projects/<project_id>/add_job', methods=['GET', 'POST'])
def add_job(project_id):

    # Generate the choices lists for the form's SelectFields
    CLIENT_NAME_CHOICES = EMPTY_SELECT_CHOICE + [(c.id, c.name) for c in Client.query.order_by('name')]
    PROJECT_NUMBER_CHOICES = EMPTY_SELECT_CHOICE + [(p.id, p.number) for p in Project.query.order_by('number')]
    PROJECT_NAME_CHOICES = EMPTY_SELECT_CHOICE + [(p.id, p.name) for p in Project.query.order_by('name')]

    # Get the chosen project 
    project = Project.query.filter_by(id=project_id).first() 

    # Create the form
    form = AddJobForm(client_name=project.client_id, project_number=project_id, project_name=project_id)

    # Add the project_id from which the new job was requested by the user to be added to
    form.project_id = project_id 

    # Assign the SelectField choices to populate in the form
    form.client_name.choices = CLIENT_NAME_CHOICES
    form.project_number.choices = PROJECT_NUMBER_CHOICES
    form.project_name.choices = PROJECT_NAME_CHOICES

    # User has added a new job
    if form.validate_on_submit():
        # Add the new job to the database
        job = Job(
            project_id=form.project_name.data,
            stage=form.stage.data,
            phase=form.phase.data            
            )
        db.session.add(job)
        db.session.commit()
        flash(f'Job "{job.stage} {job.phase}" has been added to the {job.project.name} project.')
        return redirect(url_for('main.index'))

    return render_template('add_item.html', title='Add Job', form=form, item='Job')


@bp.route('/projects/<project_id>/jobs', methods=['GET', 'POST'])
def jobs(project_id):

    jobs = Job.query.filter_by(project_id=project_id).all()

    return render_template('jobs.html', title='Job List', jobs=jobs)


@bp.route('/job/<job_id>/add_group', methods=['GET', 'POST'])
def add_group(job_id):

    # Create the form
    form = AddGroupForm()

    # Add the job_id from which the new group was requested by the user to be added to
    form.job_id.data = job_id

    # User has added a new group to an existing job
    if form.validate_on_submit():

        # Add the new group to the database
        group = Group(
            name=form.name.data,
            job_id=form.job_id.data
        )
        db.session.add(group)
        db.session.commit()
        flash(f'Group "{group.name}" has been added to the {group.job.stage} {group.job.phase} job for the {group.job.project.name} project.')
        return redirect(url_for('main.index'))

    return render_template('add_item.html', title='New Group', form=form, item="Group")

@bp.route('/job/<job_id>/groups', methods=['GET', 'POST'])
def groups(job_id):

    groups = Group.query.filter_by(job_id=job_id).all()

    return render_template('groups.html', title='Group List', groups=groups)


@bp.route('/group/<group_id>/add_channel', methods=['GET', 'POST'])
def add_channel(group_id):

    # Create the form
    form = AddChannelForm()

    # Add the group_id from which the new channel was requested by the user to be added to
    form.group_id.data = group_id

    if form.validate_on_submit():

        # Get the additional info from the form for channel creation
        testpoint_list_type = form.testpoint_list_type.data
        testpoint_list_data = form.testpoint_list.data
        num_testpoints = int(form.num_testpoints.data)
        group_id = form.group_id.data

        # Create the new channel and add it to the database
        channel = Channel(
            name=form.name.data,
            group_id=form.group_id.data,
            measurement_type=form.measurement_type.data,
            measurement_units=form.measurement_units.data,
            min_range=form.min_range.data,
            max_range=form.max_range.data,
            full_scale_range=form.full_scale_range.data,
            max_error=form.max_error.data,
            error_type=form.error_type.data,
            min_injection_range=form.min_injection_range.data,
            max_injection_range=form.max_injection_range.data,
            injection_units=form.injection_units.data,
        )
        db.session.add(channel)
        db.session.commit()
        
        # Extract the testpoint_list from the form data
        injection_values = []
        test_values = []

        # Extracts the custom TestPoint data only if selected
        if testpoint_list_type == TestPointListType.CUSTOM:
            for i, values in enumerate(testpoint_list_data):
                injection_values.append(values["injection_value"])
                test_values.append(values["test_value"])

        # Build the testpoint_list for the new channel
        channel.build_testpoint_list(num_testpoints, testpoint_list_type,
            injection_values, test_values)
        db.session.commit()
        flash(f'Channel "{channel.name}" has been added to the {channel.group.name} group along with {num_testpoints} testpoints.')
        
        return redirect(url_for(f'main.groups', job_id=channel.group.job.id))

    # Display the errors if there are any
    if len(form.errors.items()) > 0:
        print(form.errors.items())

    return render_template('add_channel.html', title='Add Channel', form=form)


@bp.route('/group/<group_id>/channels', methods=['GET', 'POST'])
def channels(group_id):

    # Get a list of all the specified Group's Channels
    group = Group.query.filter_by(id=group_id).first()
    channels = Channel.query.filter_by(group_id=group_id).all()

    # Create the master form to add each channel_form into
    channels_form = ChannelsForm()

    # TODO: Create a new class to hold all the channel, tespoint info and forms for the template

    for channel in channels:

        # Get a list of all the TestPoints in each Channel
        testpoints = channel.testpoints

        # Create the channel_form to add each testpoint_form into
        channel_form = ChannelForm()

        for testpoint in testpoints:

            # Create the testpoint_form for each testpoint
            testpoint_form = TestPointForm()

            # Add the testpoint_form into the channel_form
            channel_form.testpoints.append_entry(testpoint_form)
        
        # Add the channel_form into the master channels_form
        channels_form.channels.append_entry(channel_form)

    return render_template('channels.html', title='Channel List', channels=channels,
        channels_form=channels_form, group=group)


@bp.route('/update_testpoint', methods=['POST'])
def update_testpoint():
    
    # TestPoint Field Constants
    CHANNEL_ID = 'channel_id'
    TESTPOINT_ID = 'testpoint_id'
    MEASURED_INJECTION_VALUE = 'measured_injection_value'
    NOMINAL_INJECTION_VALUE = 'nominal_injection_value'
    MEASURED_TEST_VALUE = 'measured_test_value'
    NOMINAL_TEST_VALUE = 'nominal_test_value'
    MEASURED_ERROR = 'measured_error'
    TEST_RESULT = 'test_result'
    LAST_UPDATED = 'last_updated'
    NOTES = 'notes'

    # Variables to keep track of the updated fields
    updated_fields = []
    num_fields = 0

    # Extract the request's form dictionary
    data = request.form.to_dict()

    # Check which TestPoint is being updated
    if TESTPOINT_ID in data:
        testpoint = TestPoint.query.filter_by(id=request.form[TESTPOINT_ID]).first()

        # Remove the testpoint_id from the data to check how many parameters are being updated
        data.pop(TESTPOINT_ID)
        num_fields = len(data)
    else:
        raise ValueError(f'{TESTPOINT_ID} not found in ajax request:\n{data}')
    
    # Iterate through each field in the request and update the TestPoint accordingly
    for key, value in data.items():

        if key == MEASURED_INJECTION_VALUE:            
            testpoint.measured_injection_value = none_if_empty(value)

        if key == MEASURED_TEST_VALUE:
            testpoint.measured_test_value = none_if_empty(value)

        if key == MEASURED_ERROR:
            testpoint.measured_error = none_if_empty(value)

        if key == TEST_RESULT:
            testpoint.test_result = value

        if key == NOTES:
            testpoint.notes = value


        # Add the processed key to the list of updated fields
        updated_fields.append(key)


    # Check to make sure any fields got updated
    num_updated = len(updated_fields)
    if not num_updated == num_fields:
        raise ValueError(f'Error updating TestPoint fields. Only {num_updated}/{num_fields} updated successfully.')

    # Update the last_updated time now that changes have been made
    last_updated = datetime.utcnow()
    testpoint.last_updated = last_updated

    # Save the changes to the database
    db.session.commit()

    # Load the last_updated time into the json payload for a successful ajax request
    response = {
        'message': f'{testpoint} has successfully updated the following fields: {updated_fields}',
        'last_updated': last_updated
    }

    return jsonify(response)

