from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.models import User
#debug
from flask import flash

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password_repeat = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up !')

    # validate_<field_name> treated as custom validators besides validators=[...]
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Username Occupied. Please use another name.')

    def validate_email(self, email):
        email = User.query.filter_by(email=email.data).first()
        if email is not None:
            raise ValidationError('Email Occupied. Please use another email.')

class EditProfileForm(FlaskForm):

    def __init__(self, origin_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.origin_username = origin_username

    username = StringField('New username', validators=[DataRequired()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Save')

    def validate_username(self, username):
        #flash('origin {} new {}'.format(self.origin_username, username.data))
        if username.data != self.origin_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Username Occupied. Please use another name.')

class PostForm(FlaskForm):
    post = TextAreaField('Say something...', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')