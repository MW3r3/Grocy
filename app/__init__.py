"""
Initialization module for the Flask application.
"""

import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from flask_pymongo import PyMongo
from .routes import main as main_blueprint




def create_app(config=None):
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__)

    app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
    
    mongo = PyMongo(app)
    app.mongo = mongo


    with app.app_context():
        from .models import Item
        try:
            Item.init_collection()
        except Exception as e:
            app.logger.error("Collection creation failed: %s", e)

    if config:
        app.config.update(config)

    app.register_blueprint(main_blueprint)

    return app
