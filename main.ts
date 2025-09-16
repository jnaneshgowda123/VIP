
import { Bot, Context, InlineKeyboard } from "https://deno.land/x/grammy@v1.19.2/mod.ts";
import { MongoClient } from "https://deno.land/x/mongo@v0.32.0/mod.ts";

interface BotContext extends Context {
  session?: any;
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
      throw new Error('Missing required environment variables: BOT_TOKEN, MONGODB_URL, ADMIN_ID');
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

      await this.saveUser(userId, username);
      
      if (await this.isBannedUser(userId)) {
        await ctx.reply('❌ You are banned from using this bot.');
        return;
      }

      const isPremium = await this.isPremiumUser(userId);
      
      if (isPremium) {
        await this.checkAndInviteToChannels(ctx, userId);
        await ctx.reply('🎉 Welcome Premium Member! 💎\n\nYou have access to all premium features.\nYou\'ll receive all admin broadcasts automatically!');
      } else {
        const keyboard = new InlineKeyboard().text('💎 Buy VIP Premium', 'buy_premium');
        await ctx.reply('👋 Welcome to the bot!\n\n💎 Buy VIP Premium to access exclusive content and features!\nPremium members get instant access to all admin broadcasts.', {
          reply_markup: keyboard
        });
      }
    });

    // Admin commands
    this.bot.command('addpremium', async (ctx) => {
      if (ctx.from?.id !== this.adminId) {
        await ctx.reply('❌ Only admin can use this command!');
        return;
      }

      const args = ctx.message?.text.split(' ').slice(1);
      if (!args || args.length === 0) {
        await ctx.reply('Usage: /addpremium <user_id>');
        return;
      }

      try {
        const userId = parseInt(args[0]);
        const existing = await this.db.collection('premium_users').findOne({ user_id: userId });
        
        if (existing) {
          await ctx.reply(`User ${userId} is already a premium member!`);
          return;
        }

        await this.db.collection('premium_users').insertOne({
          user_id: userId,
          added_date: new Date(),
          added_by: this.adminId
        });

        await ctx.reply(`✅ User ${userId} has been added to premium members!`);
        console.log(`Admin added user ${userId} to premium members`);
      } catch (error) {
        await ctx.reply('❌ Invalid user ID! Please provide a valid number.');
      }
    });

    this.bot.command('removepremium', async (ctx) => {
      if (ctx.from?.id !== this.adminId) {
        await ctx.reply('❌ Only admin can use this command!');
        return;
      }

      const args = ctx.message?.text.split(' ').slice(1);
      if (!args || args.length === 0) {
        await ctx.reply('Usage: /removepremium <user_id>');
        return;
      }

      try {
        const userId = parseInt(args[0]);
        const result = await this.db.collection('premium_users').deleteOne({ user_id: userId });
        
        if (result) {
          await ctx.reply(`✅ User ${userId} has been removed from premium members!`);
          console.log(`Admin removed user ${userId} from premium members`);
        } else {
          await ctx.reply(`❌ User ${userId} is not a premium member!`);
        }
      } catch (error) {
        await ctx.reply('❌ Invalid user ID! Please provide a valid number.');
      }
    });

    this.bot.command('listpremium', async (ctx) => {
      if (ctx.from?.id !== this.adminId) {
        await ctx.reply('❌ Only admin can use this command!');
        return;
      }

      try {
        const premiumUsers = await this.db.collection('premium_users').find({}).toArray();
        
        if (premiumUsers.length === 0) {
          await ctx.reply('📋 No premium users found!');
          return;
        }

        let message = '💎 Premium Users List:\n\n';
        premiumUsers.forEach((user: any, index: number) => {
          const addedDate = new Date(user.added_date).toLocaleDateString();
          message += `${index + 1}. User ID: ${user.user_id} (Added: ${addedDate})\n`;
        });

        await ctx.reply(message);
      } catch (error) {
        await ctx.reply('❌ Error fetching premium users.');
      }
    });

    this.bot.command('banuser', async (ctx) => {
      if (ctx.from?.id !== this.adminId) {
        await ctx.reply('❌ Only admin can use this command!');
        return;
      }

      const args = ctx.message?.text.split(' ').slice(1);
      if (!args || args.length === 0) {
        await ctx.reply('Usage: /banuser <user_id>');
        return;
      }

      try {
        const userId = parseInt(args[0]);
        const existing = await this.db.collection('banned_users').findOne({ user_id: userId });
        
        if (existing) {
          await ctx.reply(`User ${userId} is already banned!`);
          return;
        }

        await this.db.collection('banned_users').insertOne({
          user_id: userId,
          banned_date: new Date(),
          banned_by: this.adminId
        });

        await ctx.reply(`✅ User ${userId} has been banned!`);
        console.log(`Admin banned user ${userId}`);
      } catch (error) {
        await ctx.reply('❌ Invalid user ID! Please provide a valid number.');
      }
    });

    this.bot.command('totalusers', async (ctx) => {
      if (ctx.from?.id !== this.adminId) {
        await ctx.reply('❌ Only admin can use this command!');
        return;
      }

      try {
        const totalUsers = await this.db.collection('all_users').countDocuments({});
        const premiumUsers = await this.db.collection('premium_users').countDocuments({});
        const bannedUsers = await this.db.collection('banned_users').countDocuments({});

        const message = `📊 User Statistics:\n\n👥 Total Users: ${totalUsers}\n💎 Premium Users: ${premiumUsers}\n🚫 Banned Users: ${bannedUsers}\n👤 Regular Users: ${totalUsers - premiumUsers - bannedUsers}`;

        await ctx.reply(message);
      } catch (error) {
        await ctx.reply('❌ Error fetching user statistics.');
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

      if (!ctx.session?.broadcast_mode) {
        await ctx.reply('❌ No active broadcast session! Use /allbroadcast first.');
        return;
      }

      const messages = ctx.session.broadcast_messages || [];
      if (messages.length === 0) {
        await ctx.reply('❌ No messages to broadcast! Send some messages first.');
        return;
      }

      await this.broadcastToAll(messages, ctx);
      ctx.session = {};
    });

    this.bot.command('stats', async (ctx) => {
      if (ctx.from?.id !== this.adminId) {
        await ctx.reply('❌ Only admin can use this command!');
        return;
      }

      try {
        const totalUsers = await this.db.collection('all_users').countDocuments({});
        const premiumUsers = await this.db.collection('premium_users').countDocuments({});
        const bannedUsers = await this.db.collection('banned_users').countDocuments({});
        const channels = await this.db.collection('premium_channels').countDocuments({});

        const message = `📊 Bot Statistics:\n\n👥 Total Users: ${totalUsers}\n💎 Premium Users: ${premiumUsers}\n🚫 Banned Users: ${bannedUsers}\n📺 Premium Channels: ${channels}\n🤖 Bot Status: Active`;

        await ctx.reply(message);
      } catch (error) {
        await ctx.reply('❌ Error fetching statistics.');
      }
    });

    // Handle user messages
    this.bot.on('message', async (ctx) => {
      const userId = ctx.from?.id;
      const username = ctx.from?.username || 'No username';

      if (!userId) return;

      await this.saveUser(userId, username);

      if (await this.isBannedUser(userId)) {
        await ctx.reply('❌ You are banned from using this bot.');
        return;
      }

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
      await this.db.collection('all_users').updateOne(
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
      const user = await this.db.collection('premium_users').findOne({ user_id: userId });
      return user !== null;
    } catch (error) {
      console.error('Error checking premium status:', error);
      return false;
    }
  }

  private async isBannedUser(userId: number): Promise<boolean> {
    try {
      const user = await this.db.collection('banned_users').findOne({ user_id: userId });
      return user !== null;
    } catch (error) {
      console.error('Error checking ban status:', error);
      return false;
    }
  }

  private async checkAndInviteToChannels(ctx: BotContext, userId: number) {
    try {
      const channels = await this.db.collection('premium_channels').find({}).toArray();
      
      for (const channel of channels) {
        try {
          const member = await ctx.api.getChatMember(channel.channel_id, userId);
          if (['member', 'administrator', 'creator'].includes(member.status)) {
            continue;
          }

          const inviteLink = await ctx.api.createChatInviteLink(channel.channel_id, {
            member_limit: 1,
            expire_date: Math.floor(Date.now() / 1000) + 3600
          });

          const message = `🎉 You've been invited to premium channel!\n\nChannel: ${channel.channel_name || 'Premium Channel'}\nLink: ${inviteLink.invite_link}\n\n⚠️ This link expires in 1 hour and is for you only!`;

          await ctx.api.sendMessage(userId, message);
          console.log(`Sent invite link to user ${userId} for channel ${channel.channel_id}`);
        } catch (error) {
          console.error(`Error inviting user ${userId} to channel ${channel.channel_id}:`, error);
        }
      }
    } catch (error) {
      console.error('Error in checkAndInviteToChannels:', error);
    }
  }

  private async handleUserMessage(ctx: BotContext) {
    const userId = ctx.from?.id;
    if (!userId) return;

    try {
      const waitMsg = await ctx.reply('🚀 Message sent to admin, wait for reply!');
      setTimeout(async () => {
        try {
          await ctx.api.deleteMessage(userId, waitMsg.message_id);
        } catch (error) {
          console.error('Error deleting wait message:', error);
        }
      }, 500);

      const username = ctx.from?.username || 'No username';
      const forwardText = `💬 Message from User:\n👤 @${username} (ID: ${userId})\n\n`;
      
      if (ctx.message?.text) {
        await ctx.api.sendMessage(this.adminId, forwardText + ctx.message.text);
      } else if (ctx.message?.photo) {
        await ctx.api.sendPhoto(this.adminId, ctx.message.photo[ctx.message.photo.length - 1].file_id, {
          caption: forwardText + (ctx.message.caption || '')
        });
      } else if (ctx.message?.document) {
        await ctx.api.sendDocument(this.adminId, ctx.message.document.file_id, {
          caption: forwardText + (ctx.message.caption || '')
        });
      } else if (ctx.message?.video) {
        await ctx.api.sendVideo(this.adminId, ctx.message.video.file_id, {
          caption: forwardText + (ctx.message.caption || '')
        });
      }
    } catch (error) {
      console.error('Error handling user message:', error);
    }
  }

  private async handleAdminMessage(ctx: BotContext) {
    if (ctx.session?.broadcast_mode) {
      const messageData: any = {};
      
      if (ctx.message?.text) {
        messageData.type = 'text';
        messageData.content = ctx.message.text;
      } else if (ctx.message?.photo) {
        messageData.type = 'photo';
        messageData.file_id = ctx.message.photo[ctx.message.photo.length - 1].file_id;
        messageData.caption = ctx.message.caption || '';
      } else if (ctx.message?.video) {
        messageData.type = 'video';
        messageData.file_id = ctx.message.video.file_id;
        messageData.caption = ctx.message.caption || '';
      } else if (ctx.message?.document) {
        messageData.type = 'document';
        messageData.file_id = ctx.message.document.file_id;
        messageData.caption = ctx.message.caption || '';
      }
      
      if (messageData.type) {
        ctx.session.broadcast_messages.push(messageData);
        await ctx.reply(`✅ Message ${ctx.session.broadcast_messages.length} collected for all broadcast! Send /done to broadcast all messages.`);
      }
      return;
    }

    await this.broadcastToPremium(ctx);
  }

  private async broadcastToPremium(ctx: BotContext) {
    try {
      const premiumUsers = await this.db.collection('premium_users').find({}).toArray();
      
      let successful = 0;
      let failed = 0;

      for (const user of premiumUsers) {
        try {
          if (ctx.message?.text) {
            await ctx.api.sendMessage(user.user_id, `📢 Premium Broadcast:\n\n${ctx.message.text}`);
          } else if (ctx.message?.photo) {
            await ctx.api.sendPhoto(user.user_id, ctx.message.photo[ctx.message.photo.length - 1].file_id, {
              caption: `📢 Premium Broadcast:\n\n${ctx.message.caption || ''}`
            });
          } else if (ctx.message?.document) {
            await ctx.api.sendDocument(user.user_id, ctx.message.document.file_id, {
              caption: `📢 Premium Broadcast:\n\n${ctx.message.caption || ''}`
            });
          } else if (ctx.message?.video) {
            await ctx.api.sendVideo(user.user_id, ctx.message.video.file_id, {
              caption: `📢 Premium Broadcast:\n\n${ctx.message.caption || ''}`
            });
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
      const allUsers = await this.db.collection('all_users').find({}).toArray();
      const bannedUsers = await this.db.collection('banned_users').find({}).toArray();
      const bannedIds = new Set(bannedUsers.map((u: any) => u.user_id));
      
      const activeUsers = allUsers.filter((user: any) => !bannedIds.has(user.user_id));
      
      let successful = 0;
      let failed = 0;

      for (const user of activeUsers) {
        try {
          for (const msg of messages) {
            if (msg.type === 'text') {
              await ctx.api.sendMessage(user.user_id, `📢 Admin Broadcast:\n\n${msg.content}`);
            } else if (msg.type === 'photo') {
              await ctx.api.sendPhoto(user.user_id, msg.file_id, {
                caption: `📢 Admin Broadcast:\n\n${msg.caption}`
              });
            } else if (msg.type === 'video') {
              await ctx.api.sendVideo(user.user_id, msg.file_id, {
                caption: `📢 Admin Broadcast:\n\n${msg.caption}`
              });
            } else if (msg.type === 'document') {
              await ctx.api.sendDocument(user.user_id, msg.file_id, {
                caption: `📢 Admin Broadcast:\n\n${msg.caption}`
              });
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
try {
  const bot = new PremiumBot();
  await bot.start();
} catch (error) {
  console.error('Failed to start bot:', error);
  throw error;
}
