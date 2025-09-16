
import { Bot, Context, InlineKeyboard } from "telegram";
import { MongoClient } from "mongodb";

interface BotContext extends Context {
  user_data?: any;
}

class PremiumBot {
  private bot: Bot<BotContext>;
  private client: MongoClient;
  private db: any;
  private adminId: number;

  constructor() {
    const botToken = Deno.env.get('BOT_TOKEN');
    const mongoUrl = Deno.env.get('MONGODB_URL');
    this.adminId = parseInt(Deno.env.get('ADMIN_ID') || '0');

    if (!botToken || !mongoUrl || !this.adminId) {
      throw new Error('Missing required environment variables');
    }

    this.bot = new Bot<BotContext>(botToken);
    this.client = new MongoClient();
    this.setupDatabase(mongoUrl);
    this.setupHandlers();
  }

  private async setupDatabase(mongoUrl: string) {
    try {
      await this.client.connect(mongoUrl);
      this.db = this.client.database('premium_bot');
      console.log('Connected to MongoDB successfully');
    } catch (error) {
      console.error('Failed to connect to MongoDB:', error);
    }
  }

  private setupHandlers() {
    // Start command
    this.bot.command('start', async (ctx) => {
      const userId = ctx.from?.id;
      const username = ctx.from?.username || 'No username';
      
      if (!userId) return;

      // Save user for broadcast purposes
      await this.saveUser(userId, username);

      const isPremium = await this.isPremiumUser(userId);
      
      if (isPremium) {
        await ctx.reply('🎉 Welcome Premium Member! 💎\n\nYou have access to all premium features.\nYou\'ll receive all admin broadcasts automatically!');
      } else {
        const keyboard = new InlineKeyboard().text('💎 Buy VIP Premium', 'buy_premium');
        await ctx.reply('👋 Welcome to the bot!\n\n💎 Buy VIP Premium to access exclusive content and features!\nPremium members get instant access to all admin broadcasts.', {
          reply_markup: keyboard
        });
      }
    });

    // All broadcast command
    this.bot.command('allbroadcast', async (ctx) => {
      if (ctx.from?.id !== this.adminId) {
        await ctx.reply('❌ Only admin can use this command!');
        return;
      }

      ctx.session = { broadcast_mode: true, broadcast_messages: [] };
      await ctx.reply('📢 All Broadcast Mode Activated!\n\nSend your messages now (text, photos, videos, documents).\nWhen you\'re done, send /done to broadcast all messages to everyone.');
    });

    // Done command
    this.bot.command('done', async (ctx) => {
      if (ctx.from?.id !== this.adminId) {
        await ctx.reply('❌ Only admin can use this command!');
        return;
      }

      const session = ctx.session as any;
      if (!session?.broadcast_mode) {
        await ctx.reply('❌ No active broadcast session! Use /allbroadcast first.');
        return;
      }

      const messages = session.broadcast_messages || [];
      if (messages.length === 0) {
        await ctx.reply('❌ No messages to broadcast! Send some messages first.');
        return;
      }

      await this.broadcastToAll(messages, ctx);
      ctx.session = {};
    });

    // Handle user messages
    this.bot.on('message', async (ctx) => {
      const userId = ctx.from?.id;
      const username = ctx.from?.username || 'No username';

      if (!userId) return;

      // Save user
      await this.saveUser(userId, username);

      // If admin message
      if (userId === this.adminId) {
        await this.handleAdminMessage(ctx);
      } else {
        await this.handleUserMessage(ctx);
      }
    });

    // Handle callback queries
    this.bot.on('callback_query:data', async (ctx) => {
      if (ctx.callbackQuery.data === 'buy_premium') {
        await ctx.answerCallbackQuery();
        await ctx.editMessageText('💎 VIP Premium Membership\n\nContact admin to purchase premium membership:\n👤 Admin: @Myhero2k\n\nPremium Benefits:\n✅ Instant access to all broadcasts\n✅ Exclusive premium channels\n✅ Priority support');
      }
    });
  }

  private async saveUser(userId: number, username: string) {
    try {
      const collection = this.db.collection('all_users');
      await collection.updateOne(
        { user_id: userId },
        {
          $set: {
            user_id: userId,
            username: username,
            last_seen: new Date()
          }
        },
        { upsert: true }
      );
    } catch (error) {
      console.error('Error saving user:', error);
    }
  }

  private async isPremiumUser(userId: number): Promise<boolean> {
    try {
      const collection = this.db.collection('premium_users');
      const user = await collection.findOne({ user_id: userId });
      return user !== null;
    } catch (error) {
      console.error('Error checking premium status:', error);
      return false;
    }
  }

  private async handleUserMessage(ctx: BotContext) {
    const userId = ctx.from?.id;
    if (!userId) return;

    // Send wait message and delete after 0.5 seconds
    const waitMsg = await ctx.reply('🚀 Message sent to admin, wait for reply!');
    setTimeout(async () => {
      try {
        await ctx.api.deleteMessage(userId, waitMsg.message_id);
      } catch (error) {
        console.error('Error deleting wait message:', error);
      }
    }, 500);

    // Forward to admin
    const username = ctx.from?.username || 'No username';
    const forwardText = `💬 Message from User:\n👤 @${username} (ID: ${userId})\n\n`;
    
    if (ctx.message?.text) {
      await ctx.api.sendMessage(this.adminId, forwardText + ctx.message.text);
    }
  }

  private async handleAdminMessage(ctx: BotContext) {
    const session = ctx.session as any;
    
    // If in broadcast collection mode
    if (session?.broadcast_mode) {
      const messageData: any = {};
      
      if (ctx.message?.text) {
        messageData.type = 'text';
        messageData.content = ctx.message.text;
      }
      
      if (messageData.type) {
        session.broadcast_messages.push(messageData);
        await ctx.reply(`✅ Message ${session.broadcast_messages.length} collected for all broadcast! Send /done to broadcast all messages.`);
      }
      return;
    }

    // Regular premium broadcast
    await this.broadcastToPremium(ctx);
  }

  private async broadcastToPremium(ctx: BotContext) {
    try {
      const collection = this.db.collection('premium_users');
      const premiumUsers = await collection.find({}).toArray();
      
      let successful = 0;
      let failed = 0;

      for (const user of premiumUsers) {
        try {
          if (ctx.message?.text) {
            await ctx.api.sendMessage(user.user_id, `📢 Premium Broadcast:\n\n${ctx.message.text}`);
          }
          successful++;
        } catch (error) {
          failed++;
        }
      }

      console.log(`Premium broadcast completed - Success: ${successful}, Failed: ${failed}`);
    } catch (error) {
      console.error('Error during premium broadcast:', error);
    }
  }

  private async broadcastToAll(messages: any[], ctx: BotContext) {
    try {
      const collection = this.db.collection('all_users');
      const bannedCollection = this.db.collection('banned_users');
      
      const allUsers = await collection.find({}).toArray();
      const bannedUsers = await bannedCollection.find({}).toArray();
      const bannedIds = new Set(bannedUsers.map(u => u.user_id));
      
      const activeUsers = allUsers.filter(user => !bannedIds.has(user.user_id));
      
      let successful = 0;
      let failed = 0;

      for (const user of activeUsers) {
        try {
          for (const msg of messages) {
            if (msg.type === 'text') {
              await ctx.api.sendMessage(user.user_id, `📢 Admin Broadcast:\n\n${msg.content}`);
            }
          }
          successful++;
        } catch (error) {
          failed++;
        }
      }

      await ctx.reply(`📊 All Broadcast Summary:\n✅ Successful: ${successful}\n❌ Failed: ${failed}\n📋 Total: ${activeUsers.length}\n📩 Messages sent: ${messages.length}`);
    } catch (error) {
      console.error('Error during all broadcast:', error);
    }
  }

  async start() {
    console.log('Bot started successfully!');
    await this.bot.start();
  }
}

// Start the bot
const bot = new PremiumBot();
bot.start();
