from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
import logging

# Basic Logging Configuration
# This will apply to all loggers unless they have more specific handlers/formatters
logging.basicConfig(
    level=logging.INFO, # Or logging.DEBUG for more verbosity during development
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# You can also configure Flask's built-in logger if preferred,
# but basicConfig often covers initial needs for libraries too.
# Example: app.logger.setLevel(logging.INFO)

app = Flask(__name__)
app.config.from_object('config.Config')

# Database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db) # Initialize Flask-Migrate

# Login manager setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = "Пожалуйста, войдите, чтобы получить доступ к этой странице."

# Import models AFTER db and migrate are initialized to avoid circular imports
from app.models import User, Role, Property 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Removed db.create_all() and manual role creation.
# This will be handled by migrations.

# Import and register blueprints
from app.admin_bp import admin_bp
app.register_blueprint(admin_bp)

from app.client_bp import client_bp 
app.register_blueprint(client_bp)   

from app.deal_bp import deal_bp 
app.register_blueprint(deal_bp)     

from app.matching_bp import matching_bp
app.register_blueprint(matching_bp)

# Global context processing
from flask import g
from app.forms import GlobalSearchForm

@app.before_request
def before_request_tasks():
    g.global_search_form = GlobalSearchForm()
    # To make it available to all templates without passing explicitly to render_template
    # This requires form to be processed from request.args if it's a GET submission in the target route

from app import routes 
