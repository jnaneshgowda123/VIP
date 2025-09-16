
import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PremiumBot:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.mongodb_url = os.getenv('MONGODB_URL')
        self.admin_id = int(os.getenv('ADMIN_ID', '0'))
        
        # MongoDB setup
        try:
            self.client = MongoClient(self.mongodb_url)
            self.db = self.client.premium_bot
            self.premium_users = self.db.premium_users
            self.broadcast_logs = self.db.broadcast_logs
            self.premium_channels = self.db.premium_channels
            self.banned_users = self.db.banned_users
            self.all_users = self.db.all_users
            logger.info("Connected to MongoDB successfully")
        except ConnectionFailure:
            logger.error("Failed to connect to MongoDB")
            
    def is_banned_user(self, user_id):
        try:
            user = self.banned_users.find_one({"user_id": user_id})
            return user is not None
        except Exception as e:
            logger.error(f"Error checking ban status: {e}")
            return False
    
    def save_user(self, user_id, username):
        try:
            self.all_users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "username": username,
                        "last_seen": datetime.now()
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        
        # Check if user is banned
        if self.is_banned_user(user_id):
            await update.message.reply_text("❌ You are banned from using this bot.")
            return
        
        # Save user to database (auto-save for broadcast purposes)
        self.save_user(user_id, username)
        
        # Check if user is premium
        is_premium = self.is_premium_user(user_id)
        
        # Log the start command
        log_message = f"User {username} (ID: {user_id}) started the bot - Premium: {is_premium}"
        logger.info(log_message)
        
        if is_premium:
            # Check and invite to premium channels if needed
            await self.check_and_invite_to_channels(update, context, user_id)
            
            welcome_message = (
                "🎉 Welcome Premium Member! 💎\n\n"
                "You have access to all premium features.\n"
                "You'll receive all admin broadcasts automatically!"
            )
            await update.message.reply_text(welcome_message)
        else:
            keyboard = [[InlineKeyboardButton("💎 Buy VIP Premium", callback_data="buy_premium")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_message = (
                "👋 Welcome to the bot!\n\n"
                "💎 Buy VIP Premium to access exclusive content and features!\n"
                "Premium members get instant access to all admin broadcasts."
            )
            await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def check_and_invite_to_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        try:
            channels = list(self.premium_channels.find())
            
            for channel in channels:
                channel_id = channel['channel_id']
                try:
                    # Check if user is already a member
                    member = await context.bot.get_chat_member(channel_id, user_id)
                    if member.status in ['member', 'administrator', 'creator']:
                        continue  # User already in channel
                        
                    # Generate invite link for this user
                    invite_link = await context.bot.create_chat_invite_link(
                        chat_id=channel_id,
                        member_limit=1,
                        expire_date=datetime.now() + timedelta(hours=1)
                    )
                    
                    invite_message = (
                        f"🎉 You've been invited to premium channel!\n\n"
                        f"Channel: {channel.get('channel_name', 'Premium Channel')}\n"
                        f"Link: {invite_link.invite_link}\n\n"
                        f"⚠️ This link expires in 1 hour and is for you only!"
                    )
                    
                    await context.bot.send_message(chat_id=user_id, text=invite_message)
                    logger.info(f"Sent invite link to user {user_id} for channel {channel_id}")
                    
                except Exception as e:
                    logger.error(f"Error checking/inviting user {user_id} to channel {channel_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in check_and_invite_to_channels: {e}")
    
    async def buy_premium_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        username = query.from_user.username or "No username"
        
        # Auto-save user for broadcast purposes
        self.save_user(user_id, username)
        
        is_premium = self.is_premium_user(user_id)
        
        if is_premium:
            await query.edit_message_text("💎 You are already a Premium Member!")
        else:
            contact_message = (
                "💎 VIP Premium Membership\n\n"
                "Contact admin to purchase premium membership:\n"
                f"👤 Admin: @Myhero2k\n\n"
                "Premium Benefits:\n"
                "✅ Instant access to all broadcasts\n"
                "✅ Exclusive premium channels\n"
                "✅ Priority support"
            )
            await query.edit_message_text(contact_message)
    
    def is_premium_user(self, user_id):
        try:
            user = self.premium_users.find_one({"user_id": user_id})
            return user is not None
        except Exception as e:
            logger.error(f"Error checking premium status: {e}")
            return False
    
    async def add_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /addpremium <user_id>")
            return
            
        try:
            user_id = int(context.args[0])
            
            # Check if user already exists
            existing_user = self.premium_users.find_one({"user_id": user_id})
            if existing_user:
                await update.message.reply_text(f"User {user_id} is already a premium member!")
                return
                
            # Add user to premium collection
            premium_user = {
                "user_id": user_id,
                "added_date": datetime.now(),
                "added_by": update.effective_user.id
            }
            
            self.premium_users.insert_one(premium_user)
            
            log_message = f"Admin added user {user_id} to premium members"
            logger.info(log_message)
            
            await update.message.reply_text(f"✅ User {user_id} has been added to premium members!")
            
            # Auto-invite to premium channels
            try:
                await self.check_and_invite_to_channels(update, context, user_id)
            except Exception as e:
                logger.error(f"Error auto-inviting new premium user to channels: {e}")
            
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID! Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error adding premium user: {e}")
            await update.message.reply_text(f"❌ Error adding user: {str(e)}")
    
    async def remove_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /removepremium <user_id>")
            return
            
        try:
            user_id = int(context.args[0])
            
            result = self.premium_users.delete_one({"user_id": user_id})
            
            if result.deleted_count > 0:
                log_message = f"Admin removed user {user_id} from premium members"
                logger.info(log_message)
                await update.message.reply_text(f"✅ User {user_id} has been removed from premium members!")
            else:
                await update.message.reply_text(f"❌ User {user_id} is not a premium member!")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID! Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error removing premium user: {e}")
            await update.message.reply_text(f"❌ Error removing user: {str(e)}")
    
    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /banuser <user_id>")
            return
            
        try:
            user_id = int(context.args[0])
            
            # Check if user already banned
            existing_ban = self.banned_users.find_one({"user_id": user_id})
            if existing_ban:
                await update.message.reply_text(f"User {user_id} is already banned!")
                return
                
            # Add user to banned collection
            banned_user = {
                "user_id": user_id,
                "banned_date": datetime.now(),
                "banned_by": update.effective_user.id
            }
            
            self.banned_users.insert_one(banned_user)
            
            log_message = f"Admin banned user {user_id}"
            logger.info(log_message)
            
            await update.message.reply_text(f"✅ User {user_id} has been banned!")
            
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID! Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            await update.message.reply_text(f"❌ Error banning user: {str(e)}")
    
    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /unbanuser <user_id>")
            return
            
        try:
            user_id = int(context.args[0])
            
            result = self.banned_users.delete_one({"user_id": user_id})
            
            if result.deleted_count > 0:
                log_message = f"Admin unbanned user {user_id}"
                logger.info(log_message)
                await update.message.reply_text(f"✅ User {user_id} has been unbanned!")
            else:
                await update.message.reply_text(f"❌ User {user_id} is not banned!")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID! Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            await update.message.reply_text(f"❌ Error unbanning user: {str(e)}")
    
    async def list_banned(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        try:
            banned_users = list(self.banned_users.find())
            
            if not banned_users:
                await update.message.reply_text("📋 No banned users found!")
                return
                
            message = "🚫 Banned Users List:\n\n"
            for i, user in enumerate(banned_users, 1):
                banned_date = user['banned_date'].strftime('%Y-%m-%d %H:%M')
                message += f"{i}. User ID: {user['user_id']} (Banned: {banned_date})\n"
                
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error listing banned users: {e}")
            await update.message.reply_text(f"❌ Error fetching banned users: {str(e)}")
    
    async def list_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        try:
            premium_users = list(self.premium_users.find())
            
            if not premium_users:
                await update.message.reply_text("📋 No premium users found!")
                return
                
            message = "💎 Premium Users List:\n\n"
            for i, user in enumerate(premium_users, 1):
                added_date = user['added_date'].strftime('%Y-%m-%d %H:%M')
                message += f"{i}. User ID: {user['user_id']} (Added: {added_date})\n"
                
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error listing premium users: {e}")
            await update.message.reply_text(f"❌ Error fetching premium users: {str(e)}")
    
    async def total_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        try:
            total_users = self.all_users.count_documents({})
            premium_users = self.premium_users.count_documents({})
            banned_users = self.banned_users.count_documents({})
            
            message = (
                f"📊 User Statistics:\n\n"
                f"👥 Total Users: {total_users}\n"
                f"💎 Premium Users: {premium_users}\n"
                f"🚫 Banned Users: {banned_users}\n"
                f"👤 Regular Users: {total_users - premium_users - banned_users}"
            )
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error fetching total users: {e}")
            await update.message.reply_text(f"❌ Error fetching user statistics: {str(e)}")
    
    async def add_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /addchannel <channel_id> [channel_name]")
            return
            
        try:
            channel_id = context.args[0]
            channel_name = " ".join(context.args[1:]) if len(context.args) > 1 else "Premium Channel"
            
            # Validate channel ID format
            if not channel_id.startswith('-') and not channel_id.startswith('@'):
                channel_id = f"-{channel_id}"
            
            # Check if channel already exists
            existing_channel = self.premium_channels.find_one({"channel_id": channel_id})
            if existing_channel:
                await update.message.reply_text(f"Channel {channel_id} is already in the premium channels list!")
                return
            
            # Try to get chat info to validate
            try:
                chat = await context.bot.get_chat(channel_id)
                channel_name = chat.title or channel_name
            except Exception as e:
                logger.warning(f"Could not get chat info for {channel_id}: {e}")
            
            # Add channel to collection
            premium_channel = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "added_date": datetime.now(),
                "added_by": update.effective_user.id
            }
            
            self.premium_channels.insert_one(premium_channel)
            
            log_message = f"Admin added channel {channel_id} ({channel_name}) to premium channels"
            logger.info(log_message)
            
            await update.message.reply_text(f"✅ Channel {channel_name} ({channel_id}) has been added to premium channels!")
            
        except Exception as e:
            logger.error(f"Error adding premium channel: {e}")
            await update.message.reply_text(f"❌ Error adding channel: {str(e)}")
    
    async def list_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        try:
            channels = list(self.premium_channels.find())
            
            if not channels:
                await update.message.reply_text("📋 No premium channels found!")
                return
                
            message = "📺 Premium Channels List:\n\n"
            for i, channel in enumerate(channels, 1):
                added_date = channel['added_date'].strftime('%Y-%m-%d %H:%M')
                message += f"{i}. {channel['channel_name']}\n   ID: {channel['channel_id']}\n   Added: {added_date}\n\n"
                
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error listing premium channels: {e}")
            await update.message.reply_text(f"❌ Error fetching premium channels: {str(e)}")
    
    async def remove_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        if not context.args:
            await update.message.reply_text("Usage: /removechannel <channel_id>")
            return
            
        try:
            channel_id = context.args[0]
            
            # Validate channel ID format
            if not channel_id.startswith('-') and not channel_id.startswith('@'):
                channel_id = f"-{channel_id}"
            
            result = self.premium_channels.delete_one({"channel_id": channel_id})
            
            if result.deleted_count > 0:
                log_message = f"Admin removed channel {channel_id} from premium channels"
                logger.info(log_message)
                await update.message.reply_text(f"✅ Channel {channel_id} has been removed from premium channels!")
            else:
                await update.message.reply_text(f"❌ Channel {channel_id} is not in the premium channels list!")
                
        except Exception as e:
            logger.error(f"Error removing premium channel: {e}")
            await update.message.reply_text(f"❌ Error removing channel: {str(e)}")
    
    async def allbroadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
        
        # Initialize broadcast mode for admin
        context.user_data['broadcast_mode'] = True
        context.user_data['broadcast_messages'] = []
        
        await update.message.reply_text(
            "📢 All Broadcast Mode Activated!\n\n"
            "Send your messages now (text, photos, videos, documents).\n"
            "When you're done, send /done to broadcast all messages to everyone."
        )
        
        logger.info("Admin activated all broadcast mode")
    
    async def done_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
        
        if not context.user_data.get('broadcast_mode'):
            await update.message.reply_text("❌ No active broadcast session! Use /allbroadcast first.")
            return
        
        broadcast_messages = context.user_data.get('broadcast_messages', [])
        
        if not broadcast_messages:
            await update.message.reply_text("❌ No messages to broadcast! Send some messages first.")
            return
        
        try:
            all_users_list = list(self.all_users.find())
            banned_users_list = list(self.banned_users.find())
            banned_ids = {user['user_id'] for user in banned_users_list}
            
            # Filter out banned users
            active_users = [user for user in all_users_list if user['user_id'] not in banned_ids]
            
            if not active_users:
                await update.message.reply_text("❌ No active users to broadcast to!")
                return
            
            successful_sends = 0
            failed_sends = 0
            
            logger.info(f"Starting all broadcast to {len(active_users)} active users with {len(broadcast_messages)} messages")
            
            # Send all collected messages to all active users
            for user in active_users:
                user_success = True
                try:
                    for msg_data in broadcast_messages:
                        if msg_data['type'] == 'text':
                            await context.bot.send_message(
                                chat_id=user['user_id'],
                                text=f"📢 Admin Broadcast:\n\n{msg_data['content']}"
                            )
                        elif msg_data['type'] == 'photo':
                            await context.bot.send_photo(
                                chat_id=user['user_id'],
                                photo=msg_data['file_id'],
                                caption=f"📢 Admin Broadcast:\n\n{msg_data.get('caption', '')}"
                            )
                        elif msg_data['type'] == 'video':
                            await context.bot.send_video(
                                chat_id=user['user_id'],
                                video=msg_data['file_id'],
                                caption=f"📢 Admin Broadcast:\n\n{msg_data.get('caption', '')}"
                            )
                        elif msg_data['type'] == 'document':
                            await context.bot.send_document(
                                chat_id=user['user_id'],
                                document=msg_data['file_id'],
                                caption=f"📢 Admin Broadcast:\n\n{msg_data.get('caption', '')}"
                            )
                    
                    if user_success:
                        successful_sends += 1
                        
                except Exception as e:
                    logger.error(f"Failed to send all broadcast messages to user {user['user_id']}: {e}")
                    failed_sends += 1
            
            # Clear broadcast mode
            context.user_data['broadcast_mode'] = False
            context.user_data['broadcast_messages'] = []
            
            # Send summary to admin
            summary = (
                f"📊 All Broadcast Summary:\n"
                f"✅ Successful: {successful_sends}\n"
                f"❌ Failed: {failed_sends}\n"
                f"📋 Total: {len(active_users)}\n"
                f"📩 Messages sent: {len(broadcast_messages)}"
            )
            
            await update.message.reply_text(summary)
            logger.info(f"All broadcast completed - Success: {successful_sends}, Failed: {failed_sends}, Messages: {len(broadcast_messages)}")
            
        except Exception as e:
            logger.error(f"Error during all broadcast: {e}")
            await update.message.reply_text(f"❌ All broadcast failed: {str(e)}")
            # Clear broadcast mode on error
            context.user_data['broadcast_mode'] = False
            context.user_data['broadcast_messages'] = []
    
    async def user_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        
        # Check if user is banned
        if self.is_banned_user(user_id):
            await update.message.reply_text("❌ You are banned from using this bot.")
            return
        
        # Save user to database
        self.save_user(user_id, username)
        
        # Skip if message is from admin
        if user_id == self.admin_id:
            return
        
        # Send "wait for reply" message to user with auto-delete after 20 seconds
        try:
            wait_message = await update.message.reply_text("🚀 Message sent to admin, wait for reply!")
            
            # Schedule deletion after 0.5 seconds
            if context.job_queue:
                context.job_queue.run_once(
                    callback=lambda job_context: self.delete_message_callback(job_context, user_id, wait_message.message_id),
                    when=0.5,
                    data={'chat_id': user_id, 'message_id': wait_message.message_id}
                )
        except Exception as e:
            logger.error(f"Error sending wait message to user: {e}")
        
        # Forward user message to admin
        try:
            forward_text = f"💬 Message from User:\n👤 @{username} (ID: {user_id})\n\n"
            
            if update.message.text:
                await context.bot.send_message(
                    chat_id=self.admin_id,
                    text=f"{forward_text}{update.message.text}"
                )
            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=self.admin_id,
                    photo=update.message.photo[-1].file_id,
                    caption=f"{forward_text}{update.message.caption or ''}"
                )
            elif update.message.document:
                await context.bot.send_document(
                    chat_id=self.admin_id,
                    document=update.message.document.file_id,
                    caption=f"{forward_text}{update.message.caption or ''}"
                )
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=self.admin_id,
                    video=update.message.video.file_id,
                    caption=f"{forward_text}{update.message.caption or ''}"
                )
            
            logger.info(f"Forwarded message from user {user_id} to admin")
            
        except Exception as e:
            logger.error(f"Error forwarding user message to admin: {e}")
    
    async def delete_message_callback(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"Auto-deleted wait message for user {chat_id}")
        except Exception as e:
            logger.error(f"Error deleting wait message for user {chat_id}: {e}")
    
    async def broadcast_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Only admin can broadcast
        if update.effective_user.id != self.admin_id:
            return
        
        # Don't broadcast commands
        if update.message.text and update.message.text.startswith('/'):
            return
        
        # Don't broadcast replies (admin responses to users)
        if update.message.reply_to_message:
            # This is a reply, handle it as admin response to user
            await self.handle_admin_reply(update, context)
            return
        
        # Check if admin is in broadcast collection mode
        if context.user_data.get('broadcast_mode'):
            # Collect messages for all broadcast
            message_data = {}
            
            if update.message.text:
                message_data = {
                    'type': 'text',
                    'content': update.message.text
                }
            elif update.message.photo:
                message_data = {
                    'type': 'photo',
                    'file_id': update.message.photo[-1].file_id,
                    'caption': update.message.caption or ''
                }
            elif update.message.video:
                message_data = {
                    'type': 'video',
                    'file_id': update.message.video.file_id,
                    'caption': update.message.caption or ''
                }
            elif update.message.document:
                message_data = {
                    'type': 'document',
                    'file_id': update.message.document.file_id,
                    'caption': update.message.caption or ''
                }
            
            if message_data:
                context.user_data['broadcast_messages'].append(message_data)
                await update.message.reply_text(f"✅ Message {len(context.user_data['broadcast_messages'])} collected for all broadcast! Send /done to broadcast all messages.")
                logger.info(f"Collected message {len(context.user_data['broadcast_messages'])} for all broadcast")
            
            return
            
        # Regular premium broadcast
        try:
            premium_users = list(self.premium_users.find())
            
            if not premium_users:
                logger.info("No premium users to broadcast to")
                return
                
            successful_sends = 0
            failed_sends = 0
            
            broadcast_log = {
                "admin_id": update.effective_user.id,
                "message_text": update.message.text or "Media message",
                "timestamp": datetime.now(),
                "total_users": len(premium_users),
                "successful_sends": 0,
                "failed_sends": 0
            }
            
            logger.info(f"Starting broadcast to {len(premium_users)} premium users")
            
            # Send message to all premium users
            for user in premium_users:
                try:
                    if update.message.text:
                        await context.bot.send_message(
                            chat_id=user['user_id'],
                            text=f"📢 Premium Broadcast:\n\n{update.message.text}"
                        )
                    elif update.message.photo:
                        await context.bot.send_photo(
                            chat_id=user['user_id'],
                            photo=update.message.photo[-1].file_id,
                            caption=f"📢 Premium Broadcast:\n\n{update.message.caption or ''}"
                        )
                    elif update.message.document:
                        await context.bot.send_document(
                            chat_id=user['user_id'],
                            document=update.message.document.file_id,
                            caption=f"📢 Premium Broadcast:\n\n{update.message.caption or ''}"
                        )
                    elif update.message.video:
                        await context.bot.send_video(
                            chat_id=user['user_id'],
                            video=update.message.video.file_id,
                            caption=f"📢 Premium Broadcast:\n\n{update.message.caption or ''}"
                        )
                    
                    successful_sends += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send message to user {user['user_id']}: {e}")
                    failed_sends += 1
            
            # Update broadcast log
            broadcast_log["successful_sends"] = successful_sends
            broadcast_log["failed_sends"] = failed_sends
            self.broadcast_logs.insert_one(broadcast_log)
            
            # Don't send summary to admin anymore
            logger.info(f"Broadcast completed - Success: {successful_sends}, Failed: {failed_sends}")
            
        except Exception as e:
            logger.error(f"Error during broadcast: {e}")
    
    async def handle_admin_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            replied_message = update.message.reply_to_message
            
            # Extract user ID from the forwarded message
            if replied_message and replied_message.text:
                # Look for user ID pattern in the forwarded message
                import re
                match = re.search(r'ID: (\d+)', replied_message.text)
                if match:
                    target_user_id = int(match.group(1))
                    
                    # Send admin's reply to the user
                    if update.message.text:
                        await context.bot.send_message(
                            chat_id=target_user_id,
                            text=f"💬 Admin Reply:\n\n{update.message.text}"
                        )
                    elif update.message.photo:
                        await context.bot.send_photo(
                            chat_id=target_user_id,
                            photo=update.message.photo[-1].file_id,
                            caption=f"💬 Admin Reply:\n\n{update.message.caption or ''}"
                        )
                    elif update.message.document:
                        await context.bot.send_document(
                            chat_id=target_user_id,
                            document=update.message.document.file_id,
                            caption=f"💬 Admin Reply:\n\n{update.message.caption or ''}"
                        )
                    elif update.message.video:
                        await context.bot.send_video(
                            chat_id=target_user_id,
                            video=update.message.video.file_id,
                            caption=f"💬 Admin Reply:\n\n{update.message.caption or ''}"
                        )
                    
                    logger.info(f"Admin replied to user {target_user_id}")
                    
        except Exception as e:
            logger.error(f"Error handling admin reply: {e}")
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("❌ Only admin can use this command!")
            return
            
        try:
            premium_count = self.premium_users.count_documents({})
            channels_count = self.premium_channels.count_documents({})
            total_users = self.all_users.count_documents({})
            banned_count = self.banned_users.count_documents({})
            recent_broadcasts = self.broadcast_logs.count_documents({
                "timestamp": {"$gte": datetime.now().replace(hour=0, minute=0, second=0)}
            })
            
            stats_message = (
                f"📊 Bot Statistics:\n\n"
                f"👥 Total Users: {total_users}\n"
                f"💎 Premium Users: {premium_count}\n"
                f"🚫 Banned Users: {banned_count}\n"
                f"📺 Premium Channels: {channels_count}\n"
                f"📢 Today's Broadcasts: {recent_broadcasts}\n"
                f"🤖 Bot Status: Active"
            )
            
            await update.message.reply_text(stats_message)
            
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            await update.message.reply_text(f"❌ Error fetching stats: {str(e)}")

def main():
    bot = PremiumBot()
    
    if not bot.bot_token:
        logger.error("BOT_TOKEN not found in environment variables")
        return
        
    if not bot.mongodb_url:
        logger.error("MONGODB_URL not found in environment variables")
        return
        
    if not bot.admin_id:
        logger.error("ADMIN_ID not found in environment variables")
        return
    
    # Create application with job queue
    from telegram.ext import JobQueue
    application = Application.builder().token(bot.bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("addpremium", bot.add_premium))
    application.add_handler(CommandHandler("removepremium", bot.remove_premium))
    application.add_handler(CommandHandler("listpremium", bot.list_premium))
    application.add_handler(CommandHandler("addchannel", bot.add_channel))
    application.add_handler(CommandHandler("listchannels", bot.list_channels))
    application.add_handler(CommandHandler("removechannel", bot.remove_channel))
    application.add_handler(CommandHandler("banuser", bot.ban_user))
    application.add_handler(CommandHandler("unbanuser", bot.unban_user))
    application.add_handler(CommandHandler("listbanned", bot.list_banned))
    application.add_handler(CommandHandler("totalusers", bot.total_users))
    application.add_handler(CommandHandler("allbroadcast", bot.allbroadcast))
    application.add_handler(CommandHandler("done", bot.done_broadcast))
    application.add_handler(CommandHandler("stats", bot.stats))
    application.add_handler(CallbackQueryHandler(bot.buy_premium_callback, pattern="buy_premium"))
    
    # Message handler for admin broadcasts (excluding commands)
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & filters.User(bot.admin_id), 
        bot.broadcast_handler
    ))
    
    # Message handler for user messages (excluding admin and commands)
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & ~filters.User(bot.admin_id), 
        bot.user_message_handler
    ))
    
    logger.info("Bot started successfully!")
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
