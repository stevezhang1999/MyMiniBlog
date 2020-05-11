from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from datetime import datetime
from app import db, login
from hashlib import md5
import jwt
from time import time
from flask import current_app
from app.search import query_index, add_to_index, remove_from_index, delete_index
import redis
import rq
import json

followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))    
)

class User(UserMixin, db.Model):

    # database part -- User model
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    last_message_read_time = db.Column(db.DateTime, default=datetime.utcnow)

    # relationship: post.author will return a user
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    # relationship: follower and followed
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    # relationship: sent and received messages
    messages_sent = db.relationship(
        'Message',          # user.messages_sent
        foreign_keys='Message.sender_id',
        backref='author',   # message_sent.author
        lazy='dynamic'
    )
    messages_received = db.relationship(
        'Message',          # user.messages_received
        foreign_keys='Message.recipient_id',
        backref='recipient',   # message_received.recipient
        lazy='dynamic'
    )

    # relationship: notification
    notifications = db.relationship(
        'Notification',
        foreign_keys='Notification.user_id',
        backref='user',   # notification.user
        lazy='dynamic'
    )

    def __repr__(self): 
        return '<User {}>'.format(self.username)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)
    
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
    
    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id
        ).count() > 0
    
    def followed_posts(self):
        """
        return a SQLAlchemy query object, user .all() or .first() to fetch posts
        """
        followed =  Post.query.join(followers, (followers.c.followed_id==Post.user_id)).filter(
            followers.c.follower_id==self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expire_in=600):
        # jwt.encode(...) return a byte sequence
        return jwt.encode({'reset_password': self.id, 'exp': time() + expire_in}, 
            current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return  Message.query.filter_by(recipient=self).filter(Message.timestamp > last_read_time).count()

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    # redis tasks
    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('app.tasks.'+name, self.id, *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)
        db.session.add(task)
        return task
    
    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()
    
    def get_first_task_in_progress_by_name(self, name):
        return Task.query.filter_by(user=self, name=name, complete=False).first()
    
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms='HS256')['reset_password']
        except:
            return
        return User.query.get(id)

# login
@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            # return empty
            return cls.query.filter_by(id=0), 0
        """
        CASE x_field
            WHEN 'f' THEN 1
            WHEN 'p' THEN 2
            WHEN 'i' THEN 3
            WHEN 'a' THEN 4
            ELSE 5 --needed only is no IN clause above. eg when = 'b'
        END, id

        case-when-value statements below is equivalent to:

        supose when[0]=(1000, 1), value=cls.id
        WHEN cls.id==1000 THEN 1

        ensure the return of sql query are the same order in ids.
        that is, the result are sorted form the most relevant (same as ES's return)

        """
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)
        ), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None
    
    @classmethod
    def reindex(cls):
        '''
        add all objects to the index
        '''
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)
    
    @classmethod
    def _delete_this_index_(cls):
        delete_index(cls.__tablename__)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

class Post(SearchableMixin ,db.Model):

    __searchable__ = ['body']

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)

class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            rq_job = None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message: {}>'.format(self.body)

class Notification(db.Model):
    # generic notification
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def __repr__(self):
        return '<Notification: {}>'.format(self.body)

    def get_data(self):
        return json.loads(str(self.payload_json))
