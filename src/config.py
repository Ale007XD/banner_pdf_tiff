import os
from typing import Dict, Any

class Config:
    """Application configuration class"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.getcwd(), 'converted')
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Conversion settings
    DEFAULT_DPI = 300
    DEFAULT_FORMAT = 'TIFF'
    
    # Create directories if they don't exist
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'max_content_length': self.MAX_CONTENT_LENGTH,
            'upload_folder': self.UPLOAD_FOLDER,
            'output_folder': self.OUTPUT_FOLDER,
            'allowed_extensions': list(self.ALLOWED_EXTENSIONS),
            'default_dpi': self.DEFAULT_DPI,
            'default_format': self.DEFAULT_FORMAT
        }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
