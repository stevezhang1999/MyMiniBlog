import os
base_dir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    # sql-alchemy configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(base_dir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ssseeecccrrreeettt'