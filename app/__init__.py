"""
Initialization module for the Flask application.
"""

import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()
from flask import Flask
from flask_pymongo import PyMongo
from .routes import main as main_blueprint




def create_app(config=None):
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY")
    
    # Get the absolute path to the certificate file
    cert_path = os.path.join(Path(__file__).parent.parent, 'isrgrootx1.pem')
    
    # Update MongoDB URI with absolute cert path
    mongo_uri = os.environ.get("MONGO_URI")
    if mongo_uri and 'tlsCAFile=' in mongo_uri:
        mongo_uri = mongo_uri.replace('tlsCAFile=./isrgrootx1.pem', f'tlsCAFile={cert_path}')
        
    app.config["MONGO_URI"] = mongo_uri
    
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
    from app.admin import admin_bp
    app.register_blueprint(admin_bp)

    return app
