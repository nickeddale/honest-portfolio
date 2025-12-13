import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask core
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if os.environ.get('FLASK_ENV') == 'production':
            raise RuntimeError("SECRET_KEY must be set in production")
        SECRET_KEY = 'dev-secret-key-change-in-production'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///portfolio.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    # Session configuration
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days

    # CSRF configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour expiry

    # Request size limit (1MB max)
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024

    # Test auth (dev mode)
    ENABLE_TEST_AUTH = os.environ.get('ENABLE_TEST_AUTH', 'False').lower() == 'true'


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    ENABLE_TEST_AUTH = True  # Always enable in dev


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    ENABLE_TEST_AUTH = False  # Never enable in prod
