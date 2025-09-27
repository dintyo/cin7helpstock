"""
Sync Service Configuration
Centralized configuration management for the sync service
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SyncConfig:
    """Configuration class for sync service"""
    
    # Sync Service Settings
    SYNC_ENABLED = os.getenv('SYNC_ENABLED', 'true').lower() == 'true'
    SYNC_OVERLAP_HOURS = int(os.getenv('SYNC_OVERLAP_HOURS', '1'))
    SYNC_MAX_ORDERS_PER_BATCH = int(os.getenv('SYNC_MAX_ORDERS_PER_BATCH', '1000'))
    SYNC_TIMEOUT_MINUTES = int(os.getenv('SYNC_TIMEOUT_MINUTES', '45'))
    SYNC_LOG_RETENTION_DAYS = int(os.getenv('SYNC_LOG_RETENTION_DAYS', '30'))
    
    # Database Settings
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'stock_forecast.db')
    
    # Cin7 API Settings
    CIN7_ACCOUNT_ID = os.getenv('CIN7_ACCOUNT_ID')
    CIN7_API_KEY = os.getenv('CIN7_API_KEY')
    CIN7_BASE_URL = os.getenv('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    # Logging Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('SYNC_LOG_FILE', 'sync_service.log')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.CIN7_ACCOUNT_ID:
            errors.append("CIN7_ACCOUNT_ID is required")
        
        if not cls.CIN7_API_KEY:
            errors.append("CIN7_API_KEY is required")
        
        if cls.SYNC_OVERLAP_HOURS < 0 or cls.SYNC_OVERLAP_HOURS > 24:
            errors.append("SYNC_OVERLAP_HOURS must be between 0 and 24")
        
        if cls.SYNC_MAX_ORDERS_PER_BATCH < 1 or cls.SYNC_MAX_ORDERS_PER_BATCH > 5000:
            errors.append("SYNC_MAX_ORDERS_PER_BATCH must be between 1 and 5000")
        
        if cls.SYNC_TIMEOUT_MINUTES < 1 or cls.SYNC_TIMEOUT_MINUTES > 180:
            errors.append("SYNC_TIMEOUT_MINUTES must be between 1 and 180")
        
        return errors
    
    @classmethod
    def get_database_path(cls):
        """Get the correct database path (handles Render persistent disk)"""
        db_path = cls.DATABASE_PATH
        
        # Check for Render persistent disk
        if db_path == 'stock_forecast.db' and os.path.exists('/data/db'):
            db_path = '/data/db/stock_forecast.db'
        
        return db_path
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive data)"""
        print("🔧 Sync Service Configuration:")
        print(f"  Sync Enabled: {cls.SYNC_ENABLED}")
        print(f"  Overlap Hours: {cls.SYNC_OVERLAP_HOURS}")
        print(f"  Max Orders/Batch: {cls.SYNC_MAX_ORDERS_PER_BATCH}")
        print(f"  Timeout Minutes: {cls.SYNC_TIMEOUT_MINUTES}")
        print(f"  Log Retention Days: {cls.SYNC_LOG_RETENTION_DAYS}")
        print(f"  Database Path: {cls.get_database_path()}")
        print(f"  Cin7 Base URL: {cls.CIN7_BASE_URL}")
        print(f"  Cin7 Account ID: {'***' + cls.CIN7_ACCOUNT_ID[-4:] if cls.CIN7_ACCOUNT_ID else 'NOT SET'}")
        print(f"  Cin7 API Key: {'***' + cls.CIN7_API_KEY[-4:] if cls.CIN7_API_KEY else 'NOT SET'}")
        print(f"  Log Level: {cls.LOG_LEVEL}")
        print(f"  Log File: {cls.LOG_FILE}")

# Example .env file content
ENV_TEMPLATE = """
# Sync Service Configuration
SYNC_ENABLED=true
SYNC_OVERLAP_HOURS=1
SYNC_MAX_ORDERS_PER_BATCH=1000
SYNC_TIMEOUT_MINUTES=45
SYNC_LOG_RETENTION_DAYS=30

# Cin7 API Configuration (REQUIRED)
CIN7_ACCOUNT_ID=your_account_id_here
CIN7_API_KEY=your_api_key_here
CIN7_BASE_URL=https://inventory.dearsystems.com/ExternalApi/v2

# Database Configuration
DATABASE_PATH=stock_forecast.db

# Logging Configuration
LOG_LEVEL=INFO
SYNC_LOG_FILE=sync_service.log

# Flask Configuration
FLASK_ENV=production
ADMIN_PASSWORD=your_admin_password_here
"""

if __name__ == '__main__':
    # Validate and print configuration
    errors = SyncConfig.validate()
    
    if errors:
        print("❌ Configuration Errors:")
        for error in errors:
            print(f"  • {error}")
        print(f"\nExample .env file:")
        print(ENV_TEMPLATE)
    else:
        print("✅ Configuration is valid!")
        SyncConfig.print_config()
