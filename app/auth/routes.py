from flask import render_template, redirect, url_for, flash, request
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from app.models import Client, Supplier, User
from app.main.forms import EMPTY_SELECT_CHOICE
from app.auth.email import send_password_reset_email


@bp.route('/login', methods=['GET', 'POST'])
def login():

    # Check to see if the current user is already registered before proceeding
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # Check to see if a validated form has been submitted in the POST request 
    form = LoginForm()
    if form.validate_on_submit():

        # Checks to ensure the user is valid
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))

        # Signs in the validated user
        login_user(user, remember=form.remember_me.data)

        # Redirect to page the user had previously specified
        # Protects against an attacker inserting a malicious URL into the next argument
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)

    return render_template('auth/login.html', title='Sign In', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():

    # Check to see if the current user is already registered before proceeding
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # Check to see if a validated form has been submitted in the POST request 
    form = RegistrationForm()

    # Generate the list of SelectField choices to populate in the form
    companies = Supplier.query.all() + Client.query.all()
    form.company.choices = EMPTY_SELECT_CHOICE + [(c.name, c.name) for c in companies.sort()]
    
    if form.validate_on_submit():

        # Add the new registered user into the database
        user = User(
            username=form.username.data,
            email=form.email.data,
            company=form.company.data,
            company_category=form.company_category.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title='Register', form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():

    # Check to see if the current user is already registered before proceeding
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # Check to see if a validated form has been submitted in the POST request 
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():

        # Email the user the password reset if valid
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    # Check to see if the current user is already registered before proceeding
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # Check if the user's reset password token is valid
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))

    # Check to see if a validated form has been submitted in the POST request 
    form = ResetPasswordForm()
    if form.validate_on_submit():

        # Set the new password for the user
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)