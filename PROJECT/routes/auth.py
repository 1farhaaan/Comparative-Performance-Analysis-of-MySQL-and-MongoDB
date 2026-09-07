from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import User
from datetime import datetime, timezone
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm, RegisterForm
from utils import dual_write_user, log_performance
import time as t
from extension import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(_dashboard_url(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(form.password.data):
            user.last_seen = datetime.now(timezone.utc)
            db.session.commit()

            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome, {user.first_name}!', 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(_dashboard_url(user))

        flash('Invalid username or password. Please try again', 'error')
    return render_template('login.html', form=form)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(_dashboard_url())

    form = RegisterForm()
    if form.validate_on_submit():
        _raw_role = request.form.get('account_type', 'client').strip().lower()
        role = _raw_role if _raw_role in ('client', 'admin') else 'client'

        t0 = t.perf_counter()
        user = User()
        user.first_name = form.first_name.data.strip()
        user.last_name = form.last_name.data.strip()
        user.email = form.email.data.lower().strip()
        user.acc_type = role
        user.company = form.company.data.strip() if form.company.data else None
        user.department = form.department.data or None

        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        mysql_ms = (t.perf_counter() - t0) * 1000
        log_performance('insert', 'mysql',mysql_ms)

        mongodb = current_app.mongo_db
        dual_write_user(mongodb, user)

        login_user(user)

        flash(f'Account created! Welcome to ResolvIQ, {user.first_name}.', 'success')
        return redirect(_dashboard_url(user))
    return render_template("signup.html", form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_password')
def forgot_password():
    flash('Password reset is not yet implemented. Contact your administrator.', 'info')
    return redirect(url_for('auth.login'))

def _dashboard_url(user=None) -> str:
    u = user if user is not None else current_user
    if u and u.is_authenticated and str(u.acc_type) == 'admin':
        return url_for('admin.dashboard')
    return url_for('client.tickets')