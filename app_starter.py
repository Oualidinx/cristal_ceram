from flask_migrate import Migrate
from root import create_app, database
from root.models import *
from flask import redirect, url_for
from dotenv import load_dotenv
import os
load_dotenv('.env')
app = create_app(os.environ.get('FLASK_ENV'))
migrate = Migrate(app=app, db = database)

@app.shell_context_processor
def make_shell_context():
    return dict(
        app = app,
        db = database
    )

@app.route('/')
def index():
    return redirect(url_for('auth_bp.login'))