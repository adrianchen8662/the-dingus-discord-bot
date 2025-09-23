# Discord AI Personality Bot

A Discord bot that responds to mentions with AI-generated responses. Each server can customize the bot's personality through system prompts.

## 🤖 Features

- **Mention Response**: Responds when you ping/mention the bot
- **Custom Personalities**: Admins can set unique AI personalities per server
- **OpenRouter Integration**: Uses OpenRouter API for access to various AI models
- **Conversation Memory**: Maintains context within message threads
- **Slash Commands**: Easy-to-use commands for configuration
- **Persistent Settings**: Personality settings are saved and restored

## 🎭 Personality Examples

### Friendly Assistant (Default)
```
You are a helpful and friendly AI assistant in a Discord server. You have a warm, conversational personality and enjoy helping users with questions, having casual conversations, and being part of the community.
```

### Sarcastic Companion
```
You are a witty, slightly sarcastic AI with a dry sense of humor. You're helpful but always ready with a clever quip or playful jab. Think of yourself as the friend who roasts you but still has your back.
```

### Gaming Buddy
```
You're an enthusiastic gaming AI who loves talking about video games, esports, and gaming culture. You use gaming terminology naturally and get excited about game discussions. You're competitive but supportive.
```

### Study Buddy
```
You're a patient, encouraging AI tutor who loves helping people learn. You break down complex topics, ask thoughtful questions, and celebrate learning achievements. You're knowledgeable but never condescending.
```

## 🚀 Setup Instructions

### 1. Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create **new application** (separate from quote bot)
3. Go to "Bot" section and create bot
4. Copy the bot token
5. Enable "Message Content Intent"

### 2. Get OpenRouter API Key
1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Go to [API Keys](https://openrouter.ai/keys)
3. Create a new API key
4. Add some credits to your account

### 3. Deploy to Portainer

#### Environment Variables:
- `DISCORD_TOKEN`: Your Discord bot token
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `SITE_URL`: Your site URL (optional, for OpenRouter rankings)
- `SITE_NAME`: Your site name (optional, for OpenRouter rankings)

#### Docker Compose Method:
1. **Stacks** → **Add Stack**
2. Name: `ai-personality-bot`
3. Upload `docker-compose-ai-bot.yml`
4. Add environment variables
5. Deploy

## 💬 Usage

### Basic Interaction
```
User: @AIBot What's the weather like?
Bot: I don't have access to real-time weather data, but I'd suggest checking your local weather app! Is there anything else I can help you with? 🌤️
```

### Admin Commands
- `/set_personality <description>` - Set custom AI personality (Admin only)
- `/get_personality` - View current personality
- `/reset_personality` - Reset to default personality (Admin only)
- `/ping_ai <message>` - Test the AI response

### Text Commands (Alternative)
- `!chat <message>` - Chat with AI via text command
- `!test` - Test bot connectivity

## ⚙️ Configuration

### Model Selection
Default: `openai/gpt-4o-mini` (cost-effective)
- Change in code: `model="openai/gpt-4o"` for more advanced responses
- Available models: Check [OpenRouter Models](https://openrouter.ai/models)

### Response Limits
- Max tokens: 300 (adjustable)
- Response splitting: Handles messages >2000 characters
- Personality limit: 1000 characters

### Cost Management
- Uses GPT-4o-mini by default (very affordable)
- Responses limited to 300 tokens
- Consider setting usage limits in OpenRouter dashboard

## 🛠️ File Structure

```
ai-personality-bot/
├── ai-personality-bot.py     # Main bot code
├── requirements-ai-bot.txt   # Python dependencies
├── Dockerfile-ai-bot         # Docker configuration
├── docker-compose-ai-bot.yml # Docker Compose setup
├── .env-ai-bot              # Environment variables
└── README.md                # This file
```

## 📊 Monitoring

### Logs to Watch For:
- `✅ Successfully synced X command(s)` - Commands loaded
- `Loaded system prompts for X guilds` - Settings restored
- Bot mention responses in chat

### Health Check:
- Use `!test` command to verify connectivity
- Use `/ping_ai` to test AI functionality
- Check OpenRouter dashboard for API usage

## 🔒 Security & Privacy

- Bot only responds to direct mentions
- System prompts saved locally (not shared)
- OpenRouter handles AI processing (check their privacy policy)
- Admin-only personality configuration
- No message history stored beyond conversation context

## 💰 Cost Estimation

With GPT-4o-mini:
- ~$0.00015 per response (300 tokens)
- 1000 responses ≈ $0.15
- Very affordable for most Discord communities

## 🎯 Best Practices

1. **Set Clear Personalities**: Be specific about tone and behavior
2. **Monitor Usage**: Keep an eye on API costs
3. **Test Personalities**: Use `/ping_ai` to test before setting
4. **Community Guidelines**: Ensure AI personality aligns with server rules
5. **Backup Settings**: System prompts are saved in `system_prompts.json`

## 🔧 Troubleshooting

### Bot Not Responding
- Check Discord token is correct
- Verify bot has "Read Messages" permission
- Ensure "Message Content Intent" is enabled

### AI Not Working
- Verify OpenRouter API key
- Check OpenRouter account has credits
- Review error logs for specific issues

### Commands Not Appearing
- Ensure bot has "Use Slash Commands" permission
- Wait a few minutes for command sync
- Try `!test` to verify basic connectivity

## 🚀 Advanced Features

### Custom Models
Change the model in the code:
```python
model="anthropic/claude-3-haiku",  # Fast and efficient
model="openai/gpt-4o",            # Most capable
model="meta-llama/llama-3-8b",    # Open source option
```

### Conversation Threading
The bot maintains context within Discord threads automatically.

### Multiple Personalities
Each Discord server can have its own unique AI personality.