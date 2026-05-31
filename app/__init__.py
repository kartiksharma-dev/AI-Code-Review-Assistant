"""
Flask Application Factory
Creates and configures the Flask application instance
"""

import os
from flask import Flask
from config import config
from app.extensions import db, login_manager, mail, jwt, limiter
from app.routes import register_routes


from flask_cors import CORS

def create_app(config_name=None):
    """
    Application factory pattern
    Creates and configures Flask app with all extensions
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create Flask instance
    app = Flask(__name__)
    
    # Enable CORS for the React frontend
    CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Register routes
    register_routes(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Configure logging
    if not app.debug and not app.testing:
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/code_review.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('AI Code Review Assistant startup')
    
    return app