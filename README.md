
# VIP Premium Telegram Bot

A comprehensive Telegram bot for managing premium memberships with MongoDB integration.

## Features

- Premium membership management
- User broadcast system (premium and all users)
- Channel invitation system
- User ban/unban functionality
- Statistics tracking
- Admin-only commands

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials
2. Install dependencies: `pip install -r requirements.txt`
3. Run the bot: `python main.py`

## Commands

### User Commands
- `/start` - Start the bot

### Admin Commands
- `/addpremium <user_id>` - Add user to premium
- `/removepremium <user_id>` - Remove user from premium
- `/listpremium` - List all premium users
- `/addchannel <channel_id> [name]` - Add premium channel
- `/listchannels` - List premium channels
- `/removechannel <channel_id>` - Remove premium channel
- `/banuser <user_id>` - Ban a user
- `/unbanuser <user_id>` - Unban a user
- `/listbanned` - List banned users
- `/totalusers` - Show user statistics
- `/allbroadcast` - Start all-user broadcast mode
- `/done` - Complete broadcast
- `/stats` - Show bot statistics

## Broadcasting

- Send any message as admin to broadcast to premium users
- Use `/allbroadcast` followed by messages, then `/done` to broadcast to all users
- Reply to forwarded user messages to respond directly

## Environment Variables

- `BOT_TOKEN` - Your Telegram bot token
- `MONGODB_URL` - MongoDB connection string
- `ADMIN_ID` - Your Telegram user ID (admin)
