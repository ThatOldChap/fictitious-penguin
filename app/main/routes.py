from flask import render_template, url_for, request, current_app, redirect, flash
from flask_login import current_user, login_required
from app import db
from app.main import bp
from app.models import User, Client, Project
from app.main.forms import EditProfileForm, AddClientForm, AddProjectForm

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():

    summary = {}

    clients = Client.query.all()
    summary["clients"] = clients

    projects = Project.query.all()
    summary["projects"] = projects

    

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

    form = AddClientForm()

    if form.validate_on_submit():

        # Add the new client to the database
        client = Client(name=form.name.data)
        db.session.add(client)
        db.session.commit()
        flash(f'Client "{client.name}" has been added to the database.')
        return redirect(url_for('main.index'))

    return render_template('add_client.html', title='Add Client', form=form)


@bp.route('/add_project', methods=['GET', 'POST'])
def add_project():

    # Create the form
    form = AddProjectForm()

    # Generate the list of Client choices to populate the Client SelectField in the form
    form.client.choices = [("", "Select Client")] + [(c.id, c.name) for c in Client.query.order_by('name')]

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

    return render_template('add_project.html', title='Add Project', form=form)