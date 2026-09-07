from dotenv import load_dotenv
import pymongo
import os

load_dotenv()


class Config:
    """Base configuration shared across all environments."""

    # ── Security ──
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    # ── MySQL / SQLAlchemy ──
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'MYSQL_URI',
        'mysql+pymysql://root:password@localhost:3306/ticket_benchmark'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,   # Recycle connections before MySQL 8hr timeout
        'pool_pre_ping': True, # Check connection health before using
    }

    # ── MongoDB ──
    mongo_client = pymongo.MongoClient(os.getenv('MONGO_URI'))
    mongo_db = mongo_client['tickets']
    mongo_col = mongo_db['complaint_tickets']

    # ── Session ──
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 30  # 30 days


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}