"""
Utility functions for the Telegram Study Battle Bot
"""

import re
from typing import List, Tuple, Optional
from telegram import User

def format_leaderboard(leaderboard: List[Tuple[str, int]], suffix: str = "questions") -> str:
    """Format leaderboard data into a readable string"""
    if not leaderboard:
        return "No data available."
    
    formatted_lines = []
    
    for i, (name, count) in enumerate(leaderboard, 1):
        # Medal emojis for top 3
        if i == 1:
            emoji = "🥇"
        elif i == 2:
            emoji = "🥈"
        elif i == 3:
            emoji = "🥉"
        else:
            emoji = f"{i}."
        
        # Format the line
        formatted_lines.append(f"{emoji} {name}: {count} {suffix}")
    
    return "\n".join(formatted_lines)

def parse_number(input_str: str) -> Optional[int]:
    """Parse a string into an integer, supporting negative numbers"""
    try:
        # Remove any whitespace
        input_str = input_str.strip()
        
        # Check if it's a valid integer (including negative)
        if re.match(r'^-?\d+$', input_str):
            return int(input_str)
        
        return None
    except (ValueError, AttributeError):
        return None

def get_user_display_name(user: User) -> str:
    """Get display name for a user"""
    if user.username:
        return f"@{user.username}"
    elif user.first_name:
        return user.first_name
    else:
        return "Unknown User"

def format_user_stats(daily: int, lifetime: int, username: Optional[str] = None) -> str:
    """Format user statistics into a readable string"""
    header = f"📊 Statistics" + (f" for {username}" if username else "")
    
    stats_lines = [
        header,
        "",
        f"📅 Today: {daily} questions",
        f"🏆 Lifetime: {lifetime} questions",
        ""
    ]
    
    # Add motivational message based on progress
    if daily == 0 and lifetime == 0:
        stats_lines.append("🎯 Ready to start your study journey?")
    elif daily == 0:
        stats_lines.append("📚 No progress today yet. Let's get started!")
    elif daily < 5:
        stats_lines.append("🌱 Good start! Keep building momentum!")
    elif daily < 10:
        stats_lines.append("🔥 Great progress today!")
    else:
        stats_lines.append("🚀 Amazing work today! You're on fire!")
    
    return "\n".join(stats_lines)

def validate_questions_count(count: int, max_allowed: int = 1000, min_allowed: int = -1000) -> Tuple[bool, str]:
    """Validate the questions count is within reasonable bounds"""
    if count > max_allowed:
        return False, f"Maximum allowed questions per update is {max_allowed}"
    
    if count < min_allowed:
        return False, f"Minimum allowed questions per update is {min_allowed}"
    
    return True, ""

def format_time_until_reset(hours: int, minutes: int) -> str:
    """Format time until next reset"""
    if hours == 0 and minutes == 0:
        return "Less than a minute"
    elif hours == 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        return f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"

def sanitize_username(username: str) -> str:
    """Sanitize username for display"""
    if not username:
        return "Unknown User"
    
    # Remove potentially problematic characters
    sanitized = re.sub(r'[^\w\s\-_@.]', '', username)
    
    # Limit length
    if len(sanitized) > 50:
        sanitized = sanitized[:47] + "..."
    
    return sanitized or "Unknown User"

def is_demo_user(username: Optional[str] = None, first_name: Optional[str] = None) -> bool:
    """Check if user is a demo user that should be excluded"""
    demo_patterns = ['demo', 'test', 'bot', 'admin_test']
    
    if username:
        username_lower = username.lower()
        if any(pattern in username_lower for pattern in demo_patterns):
            return True
    
    if first_name:
        first_name_lower = first_name.lower()
        if any(pattern in first_name_lower for pattern in demo_patterns):
            return True
        
        # Specific check for "Demo User"
        if first_name_lower == "demo user":
            return True
    
    return False

def format_command_help(command: str, description: str, example: Optional[str] = None) -> str:
    """Format help text for a command"""
    help_text = f"/{command} - {description}"
    if example:
        help_text += f"\nExample: {example}"
    return help_text

def escape_markdown(text: str) -> str:
    """Escape special markdown characters"""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def format_error_message(error_type: str, details: Optional[str] = None) -> str:
    """Format error messages consistently"""
    base_message = f"❌ {error_type}"
    
    if details:
        base_message += f"\n\n{details}"
    
    base_message += "\n\n💡 Use /help if you need assistance."
    
    return base_message

def format_success_message(action: str, details: Optional[str] = None) -> str:
    """Format success messages consistently"""
    base_message = f"✅ {action}"
    
    if details:
        base_message += f"\n\n{details}"
    
    return base_message
