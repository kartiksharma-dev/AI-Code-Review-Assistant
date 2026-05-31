"""
Data Layer - Database Models
SQLAlchemy models for persisting code reviews and analysis results
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class CodeSubmission(db.Model):
    """
    Model for storing code submissions and analysis results
    Enables history tracking and report generation
    """
    
    __tablename__ = 'code_submissions'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Submission Data
    code_text = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), default='python')
    filename = db.Column(db.String(255))
    
    # Analysis Results
    issues = db.Column(db.JSON)  # List of detected issues
    complexity_score = db.Column(db.Float)
    complexity_details = db.Column(db.JSON)  # Per-function complexity
    ai_suggestions = db.Column(db.Text)  # AI-generated recommendations
    
    # Status tracking (NEW)
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, archived
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    analysis_duration = db.Column(db.Float)  # Time taken for analysis in seconds
    
    # User Association
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def __repr__(self):
        return f'<CodeSubmission {self.id} - {self.language} - {self.created_at}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'language': self.language,
            'filename': self.filename,
            'issues_count': len(self.issues) if self.issues else 0,
            'complexity_score': self.complexity_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'analysis_duration': self.analysis_duration,
            'status': self.status
        }


class User(UserMixin, db.Model):
    """
    Model for user accounts with authentication
    Enables multi-user support and personalized history
    """
    
    __tablename__ = 'users'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # User Data
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # User Info
    full_name = db.Column(db.String(120))
    
    # Security & OTP Fields
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    otp_hash = db.Column(db.String(200))
    otp_expiry = db.Column(db.DateTime)
    otp_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_otp_sent = db.Column(db.DateTime)
    otp_locked_until = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    submissions = db.relationship('CodeSubmission', backref='user', lazy='dynamic', 
                                 order_by='CodeSubmission.created_at.desc()')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def submission_count(self):
        """Get total number of submissions by this user"""
        return self.submissions.count()
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()


class ReviewHistory(db.Model):
    """
    Model for tracking review history
    Stores complete review results with relationships to submissions and users
    """
    
    __tablename__ = 'review_history'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    code_submission_id = db.Column(db.Integer, db.ForeignKey('code_submissions.id'), nullable=False, index=True)
    
    # Review Data
    review_result = db.Column(db.Text, nullable=False)  # Complete AI review output
    language = db.Column(db.String(20))
    issues_found = db.Column(db.Integer, default=0)  # Count of issues detected
    complexity_score = db.Column(db.String(50))  # Complexity rating
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('reviews', lazy='dynamic', 
                                                      order_by='ReviewHistory.created_at.desc()'))
    submission = db.relationship('CodeSubmission', backref=db.backref('review_history', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ReviewHistory {self.id} - User {self.user_id} - {self.created_at}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'language': self.language,
            'issues_found': self.issues_found,
            'complexity_score': self.complexity_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }