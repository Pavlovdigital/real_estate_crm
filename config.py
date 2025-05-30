import os

# Construct the absolute path for the database file
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'another-secret-key-for-flask'
    # Ensure the instance folder exists when the Config is loaded or when app is initialized
    # For now, we assume 'instance' path relative to basedir.
    # Flask automatically creates the instance_path directory if it doesn't exist when app.instance_path is first accessed by Flask.
    # So, os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True) might be good here or in app factory.
    # For simplicity in config.py, we construct the path. The directory should be created before the app runs or by Flask itself.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # For Flask-WTF CSRF protection
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'a-csrf-secret-key'
