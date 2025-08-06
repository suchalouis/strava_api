#!/usr/bin/env python3
"""
Configuration management for Strava Activity Tracking Web Application
Handles environment variables and application settings using python-dotenv.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Base configuration class with default settings."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Strava API configuration
    STRAVA_CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID') or '145566'
    STRAVA_CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET') or 'd0949d11cf40903f77545b4646893c7876133585'
    STRAVA_REDIRECT_URI = os.environ.get('STRAVA_REDIRECT_URI') or 'http://localhost:5000/callback'
    
    # Application settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # Cache settings
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 3600))  # 1 hour default
    
    @staticmethod
    def validate_config():
        """Validate that required configuration is present."""
        required_vars = [
            'STRAVA_CLIENT_ID',
            'STRAVA_CLIENT_SECRET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(Config, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required configuration: {', '.join(missing_vars)}")
        
        return True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    @staticmethod
    def validate_config():
        """Additional validation for production."""
        Config.validate_config()
        
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY must be set in production")
        
        if Config.STRAVA_CLIENT_ID == '145566':
            print("WARNING: Using default Strava CLIENT_ID. Set STRAVA_CLIENT_ID environment variable.")
        
        return True


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Get current configuration
def get_config():
    """Get the current configuration based on environment."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
