"""
Bot command handlers for the Telegram Study Battle Bot
Handles all bot commands and user interactions
"""

import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from database import DatabaseManager
from utils import format_leaderboard, parse_number, get_user_display_name
from datetime import datetime

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.last_leaderboard = []  # Store last leaderboard state
        self.chat_id = None  # Store group chat ID
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not update.message:
            return
            
        user = update.effective_user
        if not user:
            return
        
        # Register user
        success = self.db.register_user(
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        welcome_message = f"""
🎯 **Welcome to Study Battle Bot!** 🎯

Hello {get_user_display_name(user)}! 

I'm here to help you track your daily study progress and compete with others!

**Available Commands:**
📚 `/solved <number>` - Log questions solved (supports negative numbers for corrections)
🏆 `/lb` - View today's leaderboard
👑 `/top` - View lifetime leaderboard
📊 `/stats` - Check your personal statistics
❓ `/help` - Show this help message

**Features:**
✅ Daily leaderboard that resets every 24 hours
✅ Lifetime statistics that never reset
✅ Support for negative corrections
✅ Automatic leaderboard updates
✅ 24/7 operation

Start logging your solved questions with `/solved <number>`!
Good luck with your studies! 📖
        """
        
        # Store chat ID for group notifications
        self.chat_id = update.message.chat_id
        await context.bot.send_message(chat_id=update.message.chat_id, text=welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not update.message:
            return
        help_message = """
🤖 **Study Battle Bot Help** 🤖

**Commands:**
📚 `/solved <number>` - Log solved questions
   Examples: `/solved 5`, `/solved -2` (for corrections)

🏆 `/lb` - Daily leaderboard (resets every 24 hours)
👑 `/top` - Lifetime leaderboard (never resets)
📊 `/stats` - Your personal statistics

**Features:**
• Daily tracking with automatic midnight reset
• Lifetime statistics preservation
• Negative number support for corrections
• Automatic leaderboard updates after logging
• Demo User exclusion from leaderboards

**Tips:**
• Use negative numbers to correct mistakes: `/solved -1`
• Daily stats reset automatically at midnight UTC
• Your lifetime stats are never reset
• Bot operates 24/7 for continuous tracking

Need more help? Contact the bot administrator!
        """
        
        await context.bot.send_message(chat_id=update.message.chat_id, text=help_message, parse_mode='Markdown')
    
    async def register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /register command (manual registration)"""
        if not update.message:
            return
            
        user = update.effective_user
        if not user:
            return
        
        success = self.db.register_user(
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        if success:
            message = f"✅ Registration successful, {get_user_display_name(user)}!\nYou can now start logging your solved questions with `/solved <number>`"
        else:
            message = "❌ Registration failed. Please try again later."
        
        await context.bot.send_message(chat_id=update.message.chat_id, text=message)
    
    async def solved_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /solved command"""
        if not update.message:
            return
            
        user = update.effective_user
        if not user:
            return
        
        # Ensure user is registered
        self.db.register_user(user.id, user.username, user.first_name, user.last_name)
        
        if not context.args:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="❌ Please specify the number of questions solved.\n"
                     "Example: `/solved 5` or `/solved -2` (for corrections)",
                parse_mode='Markdown'
            )
            return
        
        try:
            # Parse the number (supports negative numbers)
            questions_count = parse_number(context.args[0])
            
            if questions_count is None:
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="❌ Invalid number format. Please use a valid integer.\n"
                         "Examples: `5`, `-2`, `10`",
                    parse_mode='Markdown'
                )
                return
            
            # Update the database
            success = self.db.update_solved_questions(user.id, questions_count)
            
            if success:
                # Get updated stats
                stats = self.db.get_user_stats(user.id)
                daily, lifetime = stats if stats else (0, 0)
                
                if questions_count > 0:
                    message = f"✅ Great job! Added {questions_count} solved questions.\n\n"
                elif questions_count < 0:
                    message = f"✅ Correction applied: {questions_count} questions.\n\n"
                else:
                    message = f"✅ No change applied.\n\n"
                
                message += f"📊 **Your Statistics:**\n"
                message += f"📅 Today: {daily} questions\n"
                message += f"🏆 Lifetime: {lifetime} questions\n\n"
                
                # Store chat ID for notifications
                self.chat_id = update.message.chat_id
                
                await context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode='Markdown')
                
                # Check for position changes and send notifications
                await self.check_leaderboard_changes(update, context, user.id)
                
                # Auto-update leaderboard after logging questions
                await self.daily_leaderboard_command(update, context, auto_triggered=True)
                
            else:
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="❌ Failed to update your progress. Please make sure you're registered and try again."
                )
        
        except Exception as e:
            logger.error(f"Error in solved_command: {e}")
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="❌ An error occurred while processing your request. Please try again later."
            )
    
    async def daily_leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, auto_triggered: bool = False):
        """Handle /lb command (daily leaderboard)"""
        if not update.message:
            return
            
        try:
            leaderboard = self.db.get_daily_leaderboard(10)
            
            if not leaderboard:
                message = "📅 **Daily Leaderboard**\n\n🤷‍♂️ No one has solved questions today yet."
            else:
                message = "📅 **Daily Leaderboard** (Resets every 24 hours)\n\n"
                message += format_leaderboard(leaderboard, "questions today")
            
            prefix = "🔄 **Updated Leaderboard:**\n\n" if auto_triggered else ""
            await update.message.reply_text(prefix + message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in daily_leaderboard_command: {e}")
            await update.message.reply_text("❌ Error retrieving daily leaderboard. Please try again later.")
    
    async def lifetime_leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /top command (lifetime leaderboard)"""
        if not update.message:
            return
            
        try:
            leaderboard = self.db.get_lifetime_leaderboard(10)
            
            if not leaderboard:
                message = "👑 **Lifetime Leaderboard**\n\n🤷‍♂️ No lifetime statistics available yet."
            else:
                message = "👑 **Lifetime Leaderboard** (All-time)\n\n"
                message += format_leaderboard(leaderboard, "total questions")
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in lifetime_leaderboard_command: {e}")
            await update.message.reply_text("❌ Error retrieving lifetime leaderboard. Please try again later.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        if not update.message:
            return
            
        try:
            user = update.effective_user
            if not user:
                return
            
            # Ensure user is registered
            self.db.register_user(user.id, user.username, user.first_name, user.last_name)
            
            stats = self.db.get_user_stats(user.id)
            
            if stats:
                daily, lifetime = stats
                message = f"📊 **{get_user_display_name(user)}'s Statistics**\n\n"
                message += f"📅 **Today:** {daily} questions solved\n"
                message += f"🏆 **Lifetime:** {lifetime} total questions\n\n"
                
                if daily == 0 and lifetime == 0:
                    message += "🎯 Start your study journey with `/solved <number>`!"
                elif daily == 0:
                    message += "📚 No questions solved today. Time to get started!"
                else:
                    message += "🔥 Keep up the great work!"
                
            else:
                message = "❌ Unable to retrieve your statistics. Please try again later."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in stats_command: {e}")
            await update.message.reply_text("❌ Error retrieving your statistics. Please try again later.")
    
    async def reset_daily_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset_daily command (admin only - for testing)"""
        if not update.message:
            return
            
        user = update.effective_user
        if not user:
            return
        
        # Simple admin check (you can modify this to use a proper admin list)
        admin_ids = [int(x) for x in str(os.getenv('ADMIN_IDS', '')).split(',') if x.strip()]
        
        if user.id not in admin_ids and admin_ids:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        try:
            success = self.db.reset_daily_stats()
            
            if success:
                message = "✅ Daily statistics have been reset successfully!\n\n📅 All daily counts are now at 0.\n🏆 Lifetime statistics remain unchanged."
            else:
                message = "❌ Failed to reset daily statistics. Please try again."
            
            await context.bot.send_message(chat_id=update.message.chat_id, text=message)
            
        except Exception as e:
            logger.error(f"Error in reset_daily_command: {e}")
            await context.bot.send_message(chat_id=update.message.chat_id, text="❌ Error resetting daily statistics. Please try again later.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages"""
        # Let users chat normally without bot interference
        # Check if this is a special message from someone with messaging rights
        if update.message and update.message.text and not update.message.text.startswith('/'):
            await self.handle_special_message(update, context)
        pass
    
    async def check_leaderboard_changes(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Check for leaderboard position changes and notify"""
        try:
            # Get current leaderboard with IDs
            new_leaderboard = self.db.get_daily_leaderboard_with_ids(10)
            
            # Check if user moved up in ranking
            if self.last_leaderboard:
                position_change = self.db.get_user_position_change(user_id, self.last_leaderboard, new_leaderboard)
                
                if position_change:
                    old_pos, new_pos = position_change
                    
                    # Find who was outranked
                    outranked_user = None
                    for uid, name, score in self.last_leaderboard:
                        if uid != user_id:
                            # Check if this user was at the new position
                            for i, (new_uid, new_name, new_score) in enumerate(new_leaderboard, 1):
                                if uid == new_uid and i > new_pos:
                                    outranked_user = (uid, name)
                                    break
                    
                    # Send overtaking notification
                    current_user_name = get_user_display_name(update.effective_user)
                    
                    if outranked_user and self.chat_id:
                        outranked_id, outranked_name = outranked_user
                        message = f"🏆 {current_user_name} lider tablosunda {outranked_name}'i geçti! {old_pos}. sıradan {new_pos}. sıraya yükseldi!"
                        
                        await context.bot.send_message(chat_id=self.chat_id, text=message)
                        
                        # Give special message right
                        self.db.store_special_message_right(user_id, outranked_id, old_pos, new_pos)
            
            # Update last leaderboard
            self.last_leaderboard = new_leaderboard
            
        except Exception as e:
            logger.error(f"Error checking leaderboard changes: {e}")
    
    async def handle_special_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle special messages from users with messaging rights"""
        try:
            if not update.effective_user:
                return
                
            user_id = update.effective_user.id
            right_id = self.db.get_unused_message_right(user_id)
            
            if right_id:
                # User has a special message right
                message = update.message.text
                
                # Get details about who they outranked
                details = self.db.get_message_right_details(right_id)
                if details:
                    user_id, outranked_user_id, old_pos, new_pos = details
                    
                    # Get user names
                    current_user_name = get_user_display_name(update.effective_user)
                    
                    # Find outranked user name from leaderboard
                    outranked_name = "Unknown User"
                    for uid, name, score in self.last_leaderboard:
                        if uid == outranked_user_id:
                            outranked_name = name
                            break
                    
                    # Send the special message
                    special_msg = f"@everyone, {current_user_name} lider tablosunda {outranked_name}'i geçti, mesajı: {message}"
                    
                    await context.bot.send_message(chat_id=self.chat_id, text=special_msg)
                    
                    # Mark the right as used
                    self.db.use_message_right(right_id)
                    
                    # Confirm to user
                    await context.bot.send_message(
                        chat_id=update.message.chat_id, 
                        text="✅ Özel mesajın gönderildi!"
                    )
                    
        except Exception as e:
            logger.error(f"Error handling special message: {e}")
    
    async def send_daily_champion_message(self, context: ContextTypes.DEFAULT_TYPE):
        """Send daily champion message at end of day"""
        try:
            if not self.chat_id:
                return
                
            leaderboard = self.db.get_daily_leaderboard(1)
            
            if leaderboard:
                champion_name, champion_score = leaderboard[0]
                message = f"🏆 Ultimate ATPL Championship'in bugünki şampiyonu {champion_name}! 🏆"
                
                await context.bot.send_message(chat_id=self.chat_id, text=message)
            else:
                message = "🏆 Ultimate ATPL Championship'in bugün hiç katılımcısı olmadı."
                await context.bot.send_message(chat_id=self.chat_id, text=message)
                
        except Exception as e:
            logger.error(f"Error sending daily champion message: {e}")
