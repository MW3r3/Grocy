"""
Initialization module for the Flask application.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .routes import main as main_blueprint

db = SQLAlchemy()

def create_app(config=None):
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__)

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(data_dir, "site.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if config:
        app.config.update(config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(main_blueprint)

    return app
