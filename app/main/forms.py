from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length
from app.models import User
from flask import request
#debug
from flask import flash

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

class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)