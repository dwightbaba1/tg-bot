"""
Configuration settings for the Telegram Study Battle Bot
"""

import os
from typing import List

class Config:
    # Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'study_battle.db')
    
    # PostgreSQL Configuration (if using PostgreSQL instead of SQLite)
    PGHOST = os.getenv('PGHOST', 'localhost')
    PGPORT = os.getenv('PGPORT', '5432')
    PGDATABASE = os.getenv('PGDATABASE', 'study_battle')
    PGUSER = os.getenv('PGUSER', 'postgres')
    PGPASSWORD = os.getenv('PGPASSWORD', '')
    
    # Admin Configuration
    ADMIN_IDS: List[int] = []
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    if admin_ids_str:
        try:
            ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
        except ValueError:
            ADMIN_IDS = []
    
    # Bot Settings
    MAX_QUESTIONS_PER_UPDATE = int(os.getenv('MAX_QUESTIONS_PER_UPDATE', '1000'))
    MIN_QUESTIONS_PER_UPDATE = int(os.getenv('MIN_QUESTIONS_PER_UPDATE', '-1000'))
    
    # Leaderboard Settings
    DEFAULT_LEADERBOARD_SIZE = int(os.getenv('DEFAULT_LEADERBOARD_SIZE', '10'))
    MAX_LEADERBOARD_SIZE = int(os.getenv('MAX_LEADERBOARD_SIZE', '20'))
    
    # Scheduler Settings
    RESET_HOUR = int(os.getenv('RESET_HOUR', '0'))  # Hour for daily reset (0-23)
    RESET_MINUTE = int(os.getenv('RESET_MINUTE', '0'))  # Minute for daily reset (0-59)
    
    # Backup Settings
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'true').lower() == 'true'
    BACKUP_HOUR = int(os.getenv('BACKUP_HOUR', '2'))  # Hour for weekly backup
    BACKUP_DAY = int(os.getenv('BACKUP_DAY', '6'))  # Day of week for backup (0=Monday, 6=Sunday)
    
    # Health Check Settings
    HEALTH_CHECK_ENABLED = os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
    HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '60'))  # Minutes
    
    # Keep Alive Settings (for 24/7 operation)
    KEEP_ALIVE_PORT = int(os.getenv('PORT', '5000'))
    KEEP_ALIVE_HOST = os.getenv('HOST', '0.0.0.0')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Rate Limiting
    MAX_COMMANDS_PER_MINUTE = int(os.getenv('MAX_COMMANDS_PER_MINUTE', '10'))
    
    # Feature Flags
    AUTO_LEADERBOARD_UPDATE = os.getenv('AUTO_LEADERBOARD_UPDATE', 'false').lower() == 'true'
    EXCLUDE_DEMO_USERS = os.getenv('EXCLUDE_DEMO_USERS', 'true').lower() == 'true'
    ALLOW_NEGATIVE_CORRECTIONS = os.getenv('ALLOW_NEGATIVE_CORRECTIONS', 'true').lower() == 'true'
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN environment variable is required")
        
        if cls.RESET_HOUR < 0 or cls.RESET_HOUR > 23:
            errors.append("RESET_HOUR must be between 0 and 23")
        
        if cls.RESET_MINUTE < 0 or cls.RESET_MINUTE > 59:
            errors.append("RESET_MINUTE must be between 0 and 59")
        
        if cls.DEFAULT_LEADERBOARD_SIZE <= 0:
            errors.append("DEFAULT_LEADERBOARD_SIZE must be positive")
        
        if cls.MAX_LEADERBOARD_SIZE < cls.DEFAULT_LEADERBOARD_SIZE:
            errors.append("MAX_LEADERBOARD_SIZE must be >= DEFAULT_LEADERBOARD_SIZE")
        
        return errors
    
    @classmethod
    def get_postgres_url(cls) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql://{cls.PGUSER}:{cls.PGPASSWORD}@{cls.PGHOST}:{cls.PGPORT}/{cls.PGDATABASE}"
