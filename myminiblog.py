from app import db, create_app
from app.models import User, Post

app = create_app()

# The app.shell_context_processor decorator registers the function as a shell context function.
# >>> flask shell
# then could access these context
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}