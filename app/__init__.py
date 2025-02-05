"""
Initialization module for the Flask application.
"""

import os
from flask import Flask
from flask_pymongo import PyMongo
from .routes import main as main_blueprint


cert_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'isrgrootx1.pem'))

def create_app(config=None):
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__)

    app.config["MONGO_URI"] = os.environ.get(
        "MONGO_URI",
        f"mongodb+srv://Groszery:ruMDLMLsLYKm3ZXw@groszery0.qv4a4.mongodb.net/grocy?retryWrites=true&w=majority&tls=true&tlsCAFile={cert_path}&serverSelectionTimeoutMS=50000"
    )
    
    mongo = PyMongo(app)
    app.mongo = mongo

    # Initialize the 'items' collection with schema validation
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
