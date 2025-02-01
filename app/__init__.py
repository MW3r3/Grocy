import os
from flask import Flask
from .models import db

def create_app():
    app = Flask(__name__)
    
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'site.db')
    # Optional: disable track modifications to suppress FSADeprecationWarning
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    
    with app.app_context():
        from . import routes

    return app