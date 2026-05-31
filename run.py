"""
Application Entry Point
Run this file to start the Flask development server
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from app import create_app

# Create Flask application
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Run development server
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=True
    )
    
    