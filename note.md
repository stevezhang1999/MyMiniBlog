import anything form a package will run `__init__.py`

 

### IV database

 

**integration with database: ``flask-sqlalchemy``**

**db schema migration:  `flask-migrate`**

- Creating The Migration Repository `flask db init`
- Generating the migration script `flask db migrate -m [message]`
- Applying upgrade/downgrade `flask db upgrade` `flask db downgrade`



**the database model**

![1584773093286](C:\Users\hp\AppData\Roaming\Typora\typora-user-images\1584773093286.png)

usage of `db.relationship`

```python
from datetime import datetime
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    
    # virtual, maintain high-level relationship
    posts = db.relationship('Post', backref='author', lazy='dynamic')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
```



```python
p = Post(body='my first post!', author=u)
db.session.add(p)
db.session.commit(p)
```



**paly around `flask-sqlalchemy`**

```python
# query
u = User.query.all()
u = User.query.get(2)
User.query.order_by(User.username.desc()).all()

# insert
db.session.add(u)
db.session.commit()

#delete
db.session.delete(u)
db.session.commit()
```



**shell context: flask shell**

The `app.shell_context_processor` decorator registers the function as a shell context function. When the `flask shell` command runs, it will invoke this function and register the items returned by it in the shell session.

```python
from app import app, db
from app.models import User, Post

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}
```



`first_or_404()`