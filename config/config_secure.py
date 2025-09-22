"""
BaseBuilder Configuration Security Module
多角的調査により発見されたconfig/production.py import error解決用
CLAUDE.md Line 716-793: Cross-cutting architecture evaluation結果対応
"""
import os

class Config:
    """Base configuration - shared across all environments
    
    Boy Scout Rule適用: config/production.py, config/staging.pyで共通使用される
    基底設定クラス。import error解決とDRY原則適用のため作成。
    """
    
    # Core Security Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Database Configuration (RDS)
    DB_USERNAME = os.getenv('DB_USERNAME', 'QuestEd')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'QuestEd-03012025MySQL')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'quested')
    
    # Flask-SQLAlchemy Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'charset': 'utf8mb4',
            'init_command': 'SET sql_mode="STRICT_TRANS_TABLES"'
        }
    }
    
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        """Database URI construction with proper escaping"""
        return f"mysql+pymysql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Performance & Caching
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block'
    }