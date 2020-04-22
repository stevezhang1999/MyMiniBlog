from flask import render_template, flash, redirect, url_for, request
from werkzeug.urls import url_parse

from app import db
# from app.auth.forms import LoginForm, RegisterationForm, ResetPasswordRequest, ResetPasswordForm
from app.auth.forms import LoginForm, RegisterationForm, ResetPasswordForm, ResetPasswordRequest
from app.models import User, Post
from app.auth.email import send_password_reset_email

from flask_login import current_user, login_user
from flask_login import logout_user
from flask_login import login_required

from datetime import datetime

from app.auth import bp

@bp.before_request
def before_request():
    if current_user:
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            db.session.commit()

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
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
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegisterationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, registration succeed!')
        return redirect(url_for('main.index'))
    
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequest()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash("A email has been sent!")
            return redirect(url_for('main.index'))
        else:
            flash('Email not found')
            return redirect(url_for('auth.reset_password_request', title='Reset Password', form=form))
        
    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form)
    
@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)

    if not user:
        flash("Reset link expired or not exist.")
        return redirect(url_for('auth.login'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password had been changed.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
