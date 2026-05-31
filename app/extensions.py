"""
Flask Extensions
Centralized initialization of Flask extensions to avoid circular imports
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize SQLAlchemy
db = SQLAlchemy()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize Mail
mail = Mail()

# Initialize JWT
jwt = JWTManager()

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)