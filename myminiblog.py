from app import app, db
from app.models import User, Post

# The app.shell_context_processor decorator registers the function as a shell context function.
# >>> flask shell
# then could access these context
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}