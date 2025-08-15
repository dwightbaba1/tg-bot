"""
Database management for the Telegram Study Battle Bot
Handles SQLite database operations for user data and leaderboards
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Union
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "study_battle.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create daily_stats table (resets every 24 hours)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        user_id INTEGER PRIMARY KEY,
                        questions_solved INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Create lifetime_stats table (never resets)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS lifetime_stats (
                        user_id INTEGER PRIMARY KEY,
                        total_questions INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Create daily_reset_log table to track resets
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_reset_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        reset_date DATE,
                        reset_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def register_user(self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Register a new user or update existing user info"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    # Update existing user
                    cursor.execute('''
                        UPDATE users 
                        SET username = ?, first_name = ?, last_name = ?
                        WHERE user_id = ?
                    ''', (username, first_name, last_name, user_id))
                else:
                    # Insert new user
                    cursor.execute('''
                        INSERT INTO users (user_id, username, first_name, last_name)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, username, first_name, last_name))
                    
                    # Initialize stats for new user
                    cursor.execute('''
                        INSERT OR IGNORE INTO daily_stats (user_id, questions_solved)
                        VALUES (?, 0)
                    ''', (user_id,))
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO lifetime_stats (user_id, total_questions)
                        VALUES (?, 0)
                    ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            return False
    
    def update_solved_questions(self, user_id: int, questions_count: int) -> bool:
        """Update solved questions count (can be negative for corrections)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ensure user is registered
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                if not cursor.fetchone():
                    return False
                
                # Update daily stats
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_stats (user_id, questions_solved, last_updated)
                    VALUES (?, 
                            COALESCE((SELECT questions_solved FROM daily_stats WHERE user_id = ?), 0) + ?,
                            CURRENT_TIMESTAMP)
                ''', (user_id, user_id, questions_count))
                
                # Update lifetime stats (only if positive or if it doesn't make total negative)
                cursor.execute("SELECT total_questions FROM lifetime_stats WHERE user_id = ?", (user_id,))
                current_lifetime = cursor.fetchone()
                current_lifetime = current_lifetime[0] if current_lifetime else 0
                
                new_lifetime = max(0, current_lifetime + questions_count)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO lifetime_stats (user_id, total_questions, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, new_lifetime))
                
                # Ensure daily stats don't go negative
                cursor.execute("SELECT questions_solved FROM daily_stats WHERE user_id = ?", (user_id,))
                current_daily = cursor.fetchone()
                if current_daily and current_daily[0] < 0:
                    cursor.execute('''
                        UPDATE daily_stats SET questions_solved = 0 WHERE user_id = ?
                    ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating solved questions for user {user_id}: {e}")
            return False
    
    def get_daily_leaderboard_with_ids(self, limit: int = 10) -> List[Tuple[int, str, int]]:
        """Get daily leaderboard with user IDs"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        u.user_id,
                        COALESCE(u.username, u.first_name, 'Unknown User') as display_name,
                        d.questions_solved
                    FROM daily_stats d
                    JOIN users u ON d.user_id = u.user_id
                    WHERE d.questions_solved > 0 
                    AND COALESCE(u.username, u.first_name, '') != 'Demo User'
                    ORDER BY d.questions_solved DESC
                    LIMIT ?
                ''', (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting daily leaderboard with IDs: {e}")
            return []

    def get_daily_leaderboard(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get daily leaderboard (excludes Demo User)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COALESCE(u.username, u.first_name, 'Unknown User') as display_name,
                        d.questions_solved
                    FROM daily_stats d
                    JOIN users u ON d.user_id = u.user_id
                    WHERE d.questions_solved > 0 
                    AND COALESCE(u.username, u.first_name, '') != 'Demo User'
                    ORDER BY d.questions_solved DESC
                    LIMIT ?
                ''', (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting daily leaderboard: {e}")
            return []
    
    def get_lifetime_leaderboard(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get lifetime leaderboard (excludes Demo User)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COALESCE(u.username, u.first_name, 'Unknown User') as display_name,
                        l.total_questions
                    FROM lifetime_stats l
                    JOIN users u ON l.user_id = u.user_id
                    WHERE l.total_questions > 0 
                    AND COALESCE(u.username, u.first_name, '') != 'Demo User'
                    ORDER BY l.total_questions DESC
                    LIMIT ?
                ''', (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting lifetime leaderboard: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Optional[Tuple[int, int]]:
        """Get user's daily and lifetime stats"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COALESCE(d.questions_solved, 0) as daily,
                        COALESCE(l.total_questions, 0) as lifetime
                    FROM users u
                    LEFT JOIN daily_stats d ON u.user_id = d.user_id
                    LEFT JOIN lifetime_stats l ON u.user_id = l.user_id
                    WHERE u.user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result if result else (0, 0)
                
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return None
    
    def reset_daily_stats(self) -> bool:
        """Reset all daily statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Reset daily stats
                cursor.execute("UPDATE daily_stats SET questions_solved = 0, last_updated = CURRENT_TIMESTAMP")
                
                # Log the reset
                cursor.execute('''
                    INSERT INTO daily_reset_log (reset_date)
                    VALUES (DATE('now'))
                ''')
                
                conn.commit()
                logger.info("Daily stats reset successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting daily stats: {e}")
            return False
    
    def get_total_users(self) -> int:
        """Get total number of registered users"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting total users: {e}")
            return 0
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of the database"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backup_study_battle_{timestamp}.db"
            
            # Simple file copy for SQLite
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return False
    
    def get_user_position_change(self, user_id: int, old_leaderboard: List[Tuple[int, str, int]], new_leaderboard: List[Tuple[int, str, int]]) -> Optional[Tuple[int, int]]:
        """Get user's position change (old_pos, new_pos) or None if no change"""
        try:
            old_pos = None
            new_pos = None
            
            # Find positions in both leaderboards
            for i, (uid, name, score) in enumerate(old_leaderboard, 1):
                if uid == user_id:
                    old_pos = i
                    break
            
            for i, (uid, name, score) in enumerate(new_leaderboard, 1):
                if uid == user_id:
                    new_pos = i
                    break
            
            # Return change only if user improved position
            if old_pos is not None and new_pos is not None and new_pos < old_pos:
                return (old_pos, new_pos)
            elif old_pos is None and new_pos is not None:
                # New entry to leaderboard
                return (len(old_leaderboard) + 1, new_pos)
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting user position change: {e}")
            return None
    
    def store_special_message_right(self, user_id: int, outranked_user_id: int, old_pos: int, new_pos: int) -> bool:
        """Store special message right for user who outranked another"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create special_message_rights table if not exists
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS special_message_rights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        outranked_user_id INTEGER,
                        old_position INTEGER,
                        new_position INTEGER,
                        used BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (outranked_user_id) REFERENCES users (user_id)
                    )
                ''')
                
                cursor.execute('''
                    INSERT INTO special_message_rights (user_id, outranked_user_id, old_position, new_position)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, outranked_user_id, old_pos, new_pos))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing special message right: {e}")
            return False
    
    def get_unused_message_right(self, user_id: int) -> Optional[int]:
        """Get unused message right ID for user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id FROM special_message_rights 
                    WHERE user_id = ? AND used = FALSE 
                    ORDER BY created_at DESC LIMIT 1
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Error getting unused message right: {e}")
            return None
    
    def use_message_right(self, right_id: int) -> bool:
        """Mark message right as used"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE special_message_rights SET used = TRUE WHERE id = ?
                ''', (right_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error using message right: {e}")
            return False
    
    def get_message_right_details(self, right_id: int) -> Optional[Tuple[int, int, int, int]]:
        """Get message right details (user_id, outranked_user_id, old_pos, new_pos)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_id, outranked_user_id, old_position, new_position
                    FROM special_message_rights WHERE id = ?
                ''', (right_id,))
                
                return cursor.fetchone()
                
        except Exception as e:
            logger.error(f"Error getting message right details: {e}")
            return None
