
# Premium Telegram Bot

A Telegram bot that automatically broadcasts admin messages to premium users with MongoDB integration.

## Features

- 🎯 Auto-broadcast admin messages to premium users only
- 💎 Premium user management system
- 📊 Live logging and statistics
- 🛡️ Admin-only commands
- 📱 Interactive inline keyboards
- 🗄️ MongoDB integration for data persistence
- 🚀 User message forwarding with auto-reply
- 📺 Premium channel management with auto-invites
- 🚫 User ban/unban system

## Setup Instructions

1. **Create a Telegram Bot:**
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Copy the bot token

2. **Get your Admin ID:**
   - Message @userinfobot on Telegram
   - Copy your user ID

3. **Set up MongoDB:**
   - Create a MongoDB database (MongoDB Atlas recommended)
   - Get your connection URL

4. **Configure Environment Variables:**
   - Copy `.env.example` to `.env`
   - Fill in your bot token, MongoDB URL, and admin ID

5. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the Bot:**
   ```bash
   python main.py
   ```

## Commands

### Admin Commands:

#### Premium User Management:
- `/addpremium <user_id>` - Add user to premium list
- `/removepremium <user_id>` - Remove user from premium list
- `/listpremium` - View all premium users

#### Channel Management:
- `/addchannel <channel_id> [channel_name]` - Add premium channel for auto-invites
- `/listchannels` - View all premium channels
- `/removechannel <channel_id>` - Remove channel from premium list

#### User Management:
- `/banuser <user_id>` - Ban user from using the bot
- `/unbanuser <user_id>` - Unban user
- `/listbanned` - View all banned users
- `/totalusers` - View user statistics

#### Broadcasting:
- `/allbroadcast` - Start collecting messages for broadcast to all users (premium and non-premium)
- `/done` - Complete broadcast session and send all collected messages
- **Direct messaging** - Any non-command message from admin automatically broadcasts to premium users only

#### Statistics:
- `/stats` - View comprehensive bot statistics

### User Commands:
- `/start` - Start the bot, check premium status, and get auto-invited to premium channels (if premium)

## Auto-Features

### Auto-Broadcasting
When an admin sends any message (text, photo, video, document) directly to the bot (not as a command), it will automatically be forwarded to all premium users with a "📢 Premium Broadcast:" prefix.

### User Message Forwarding
- When any user sends a message to the bot, they receive "🚀 Message sent to admin, wait for reply!" (auto-deletes after 20 seconds)
- The message is automatically forwarded to the admin with user details
- Admin can reply by replying to the forwarded message
- All user interactions are automatically saved for broadcast purposes

### Multi-Step Broadcasting
- Use `/allbroadcast` to start collecting messages for broadcast
- Send multiple messages (text, photos, videos, documents)
- Use `/done` to broadcast all collected messages to all users
- Each user receives all messages in sequence with broadcast prefixatically saved for broadcast purposes

### Premium Channel Auto-Invite
- When premium users use `/start`, the bot automatically checks their membership in premium channels
- If not a member, generates unique invite links (1-person limit, 1-hour expiry)
- Sends invite links directly to the user

### Buy Premium Button
- Non-premium users see a "💎 Buy VIP Premium" button
- Button shows contact information for admin (@Myhero2k)
- Button only appears for non-premium users

## Live Logging

The bot logs all activities including:
- User starts and premium status checks
- Premium user additions/removals
- Channel management actions
- Broadcast statistics
- User message forwarding
- Error handling
- Ban/unban actions

All logs are visible in the console and stored in MongoDB for persistence.

## Database Collections

- `premium_users` - Stores premium user data
- `premium_channels` - Stores premium channel configurations
- `banned_users` - Stores banned user data
- `all_users` - Stores all user interactions for broadcasts
- `broadcast_logs` - Stores broadcast statistics and history

## Security Features

- Admin-only command restrictions
- Banned user filtering
- Automatic user validation
- MongoDB connection error handling
- Comprehensive logging for audit trails
