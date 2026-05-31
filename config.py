"""
Application Configuration
Centralized configuration for the AI Code Review Assistant
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class"""
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///code_review.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1MB max file size
    ALLOWED_EXTENSIONS = {'py', 'js', 'java', 'cpp', 'c', 'txt'}
    
    # Analysis Settings
    MAX_CODE_LENGTH = 50000  # Maximum characters in code submission
    COMPLEXITY_THRESHOLD = 10  # Cyclomatic complexity warning threshold
    
    # AI Settings (for future Anthropic API integration)
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    AI_MAX_TOKENS = 1000
    
    # Session Settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # JWT Settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Mail Settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    MAIL_DEBUG = True  # Enable deep SMTP transaction logging for debugging
    
    # Resend Settings
    MAIL_PROVIDER = os.environ.get('MAIL_PROVIDER', 'gmail').lower()
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY')


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}