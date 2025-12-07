from flask import Flask
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update({
        "SECRET_KEY": os.environ.get("FLASK_SECRET_KEY", "change-me-in-prod"),
        "SQLALCHEMY_DATABASE_URI": "sqlite:///users.db",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_TIME_LIMIT": None,
        "MONGO_URI": os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
        "MONGO_DB": os.environ.get("MONGO_DB", "healthcare"),
        "MONGO_COLLECTION": os.environ.get("MONGO_COLLECTION", "strokes"),
        "FERNET_KEY": os.environ.get("FERNET_KEY", ""),
        "ADMIN_SECRET_CODE": os.environ.get("ADMIN_SECRET_CODE", "admin123"),
        # Secure session handling
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": 3600,
    })
    if config:
        app.config.update(config)

    db.init_app(app)
    csrf.init_app(app)
   
    # create DB tables
    with app.app_context():
        db.create_all()

    # Check MongoDB connection
    try:
        mongo_client = MongoClient(app.config["MONGO_URI"])
        mongo_client.server_info() 
        dbname = os.environ.get("MONGO_DB", "healthcare")
        collname = os.environ.get("MONGO_COLLECTION", "strokes")
        print("Database name:", dbname)
        print("Database name:", collname)
        print("MongoDB connected successfully.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")

    # register blueprints (auth and dashboard routes)
    from app.route import auth_bp
  
    app.register_blueprint(auth_bp)


    return app