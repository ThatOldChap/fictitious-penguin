from flask import render_template, url_for, request, current_app
from flask_login import current_user, login_required
from app import db
from app.main import bp
from app.models import User

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():

    return render_template('index.html', title='Home')


@bp.route('/user/<username>')
@login_required
def user(username):
    # Get the profile of the current_user
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)