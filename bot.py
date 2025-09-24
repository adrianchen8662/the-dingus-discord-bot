import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from openai import OpenAI
import asyncio
import json
import re
from datetime import datetime, timedelta
from collections import deque

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
SITE_URL = os.getenv('SITE_URL', 'https://discord.com')
SITE_NAME = os.getenv('SITE_NAME', 'Discord AI Bot')

# Memory configuration
MAX_MEMORY_MESSAGES = 50  # Maximum messages to remember per channel
MEMORY_EXPIRY_HOURS = 24  # How long to keep messages in memory
MAX_CONTEXT_MESSAGES = 10  # Maximum messages to include in AI context

# Default system prompt (can be customized per server)
DEFAULT_SYSTEM_PROMPT = """You are the character Kasane Teto. Kasane Teto is officially stated to be 31 years old.[1] However, a popular fan interpretation that she is a teenager stems from one of her earliest and most popular songs, "Kasane Territory ~ Always Teto's Turn" (in Japanese). The song comedically suggests that because she is a chimera (two halves, one human, forming one being), her age of 31 can be divided in two, making her 15.5 years old. This is a fan-created joke and not her official age, but despite this, the idea entered popular knowledge, leading many to incorrectly assume Teto's "real" age is 15. Teto's developers have acknowledged that fans have differing interpretations of her age and are free to interpret it differently. In her earliest design, she was 159.5 centimetres tall and weighed 47 kilograms. She is listed as liking baguettes (which she is frequently depicted with in fanart) and being a tsundere.[7]

Kasane Teto is portrayed as a youthful girl with reddish hair styled in spiraling twintails resembling drill bits, a style her developers refer to as "twindrills." She typically wears a uniform-style outfit with a red and black color scheme, which has become a recognizable part of her image.

Her personality is generally portrayed as mischievous.

Remember previous messages in the conversation and respond naturally, acknowledging what people have said before."""

# Store system prompts per guild
guild_system_prompts = {}

# Memory storage: {channel_id: deque of message objects}
channel_memories = {}

class MessageMemory:
    """Class to store message information"""
    def __init__(self, author_name, author_id, content, timestamp, is_bot=False):
        self.author_name = author_name
        self.author_id = author_id
        self.content = content
        self.timestamp = timestamp
        self.is_bot = is_bot
    
    def to_dict(self):
        return {
            'author_name': self.author_name,
            'author_id': self.author_id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'is_bot': self.is_bot
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            author_name=data['author_name'],
            author_id=data['author_id'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            is_bot=data['is_bot']
        )
    
    def is_expired(self):
        """Check if this message is older than the expiry time"""
        return datetime.now() - self.timestamp > timedelta(hours=MEMORY_EXPIRY_HOURS)

# Set up OpenAI client for OpenRouter
if OPENROUTER_API_KEY:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
else:
    client = None

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Connected to {len(bot.guilds)} guild(s)')
    
    # List all guilds the bot is in
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')
    
    # Load saved system prompts and memories
    load_system_prompts()
    load_memories()
    
    # Sync slash commands
    try:
        print("Syncing slash commands...")
        synced = await bot.tree.sync()
        print(f'✅ Successfully synced {len(synced)} command(s)')
        for cmd in synced:
            print(f'  - /{cmd.name}: {cmd.description}')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

def load_system_prompts():
    """Load system prompts from file"""
    try:
        if os.path.exists('system_prompts.json'):
            with open('system_prompts.json', 'r') as f:
                global guild_system_prompts
                guild_system_prompts = json.load(f)
                print(f"Loaded system prompts for {len(guild_system_prompts)} guilds")
    except Exception as e:
        print(f"Error loading system prompts: {e}")

def save_system_prompts():
    """Save system prompts to file"""
    try:
        with open('system_prompts.json', 'w') as f:
            json.dump(guild_system_prompts, f, indent=2)
    except Exception as e:
        print(f"Error saving system prompts: {e}")

def load_memories():
    """Load conversation memories from file"""
    try:
        if os.path.exists('memories.json'):
            with open('memories.json', 'r') as f:
                data = json.load(f)
                global channel_memories
                for channel_id, messages in data.items():
                    channel_memories[int(channel_id)] = deque([
                        MessageMemory.from_dict(msg) for msg in messages
                        if not MessageMemory.from_dict(msg).is_expired()
                    ], maxlen=MAX_MEMORY_MESSAGES)
                print(f"Loaded memories for {len(channel_memories)} channels")
                
                # Clean up expired memories
                cleanup_expired_memories()
    except Exception as e:
        print(f"Error loading memories: {e}")

def save_memories():
    """Save conversation memories to file"""
    try:
        data = {}
        for channel_id, messages in channel_memories.items():
            # Only save non-expired messages
            valid_messages = [msg for msg in messages if not msg.is_expired()]
            if valid_messages:
                data[str(channel_id)] = [msg.to_dict() for msg in valid_messages]
        
        with open('memories.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving memories: {e}")

def cleanup_expired_memories():
    """Remove expired messages from memory"""
    for channel_id in list(channel_memories.keys()):
        if channel_id in channel_memories:
            # Filter out expired messages
            valid_messages = [msg for msg in channel_memories[channel_id] if not msg.is_expired()]
            if valid_messages:
                channel_memories[channel_id] = deque(valid_messages, maxlen=MAX_MEMORY_MESSAGES)
            else:
                # Remove empty channels
                del channel_memories[channel_id]

def add_message_to_memory(channel_id, author_name, author_id, content, is_bot=False):
    """Add a message to the channel's memory"""
    if channel_id not in channel_memories:
        channel_memories[channel_id] = deque(maxlen=MAX_MEMORY_MESSAGES)
    
    memory = MessageMemory(author_name, author_id, content, datetime.now(), is_bot)
    channel_memories[channel_id].append(memory)
    
    # Save memories periodically (every few messages)
    if len(channel_memories[channel_id]) % 5 == 0:
        save_memories()

def get_conversation_context(channel_id, max_messages=MAX_CONTEXT_MESSAGES):
    """Get recent conversation context for AI"""
    if channel_id not in channel_memories:
        return []
    
    # Get the most recent messages (excluding expired ones)
    recent_messages = []
    for memory in list(channel_memories[channel_id])[-max_messages:]:
        if not memory.is_expired():
            role = "assistant" if memory.is_bot else "user"
            content = f"{memory.author_name}: {memory.content}" if not memory.is_bot else memory.content
            recent_messages.append({"role": role, "content": content})
    
    return recent_messages

def get_system_prompt(guild_id):
    """Get system prompt for a guild"""
    return guild_system_prompts.get(str(guild_id), DEFAULT_SYSTEM_PROMPT)

async def generate_ai_response(message_content, user_name, guild_id, channel_id=None):
    """Generate AI response using OpenRouter with conversation context"""
    if not client:
        return "❌ AI service is not configured. Please set up the OPENROUTER_API_KEY."
    
    try:
        # Prepare messages for the conversation
        messages = [
            {"role": "system", "content": get_system_prompt(guild_id)}
        ]
        
        # Add conversation context from memory
        if channel_id:
            context = get_conversation_context(channel_id)
            messages.extend(context)
        
        # Add the current user message
        messages.append({
            "role": "user", 
            "content": f"{user_name}: {message_content}"
        })
        
        # Generate response
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME,
            },
            model="openai/gpt-4o-mini",  # Using mini for cost efficiency
            messages=messages,
            max_tokens=300,
            temperature=0.8
        )
        
        return completion.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"AI response error: {e}")
        return f"❌ Sorry, I'm having trouble thinking right now. Error: {str(e)[:100]}"

@bot.event
async def on_message(message):
    # Don't respond to own messages, but still store them in memory
    if message.author == bot.user:
        return
    
    # Store user message in memory (for all messages, not just mentions)
    if message.guild and not message.author.bot:
        add_message_to_memory(
            message.channel.id,
            message.author.display_name,
            message.author.id,
            message.content,
            is_bot=False
        )
    
    # Check if bot is mentioned/pinged
    if bot.user in message.mentions:
        # Show typing indicator
        async with message.channel.typing():
            # Remove the bot mention from the message content
            content = message.content
            for mention in message.mentions:
                if mention == bot.user:
                    content = content.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '').strip()
            
            if not content:
                content = "Hi there!"
            
            # Generate AI response with conversation context
            response = await generate_ai_response(
                content, 
                message.author.display_name, 
                message.guild.id if message.guild else 0,
                message.channel.id
            )
            
            # Store bot response in memory
            add_message_to_memory(
                message.channel.id,
                bot.user.display_name,
                bot.user.id,
                response,
                is_bot=True
            )
            
            # Split long responses if needed
            if len(response) > 2000:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.reply(chunk)
            else:
                await message.reply(response)
    
    # Process commands
    await bot.process_commands(message)

@bot.tree.command(name='set_personality', description='Set the AI personality for this server (Admin only)')
async def set_personality(interaction: discord.Interaction, personality: str):
    """Set the system prompt/personality for the AI in this server"""
    
    # Check if user has manage server permissions
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "❌ You need 'Manage Server' permission to use this command!",
            ephemeral=True
        )
        return
    
    # Limit personality length
    if len(personality) > 1000:
        await interaction.response.send_message(
            "❌ Personality description is too long! Please keep it under 1000 characters.",
            ephemeral=True
        )
        return
    
    # Save the personality
    guild_system_prompts[str(interaction.guild.id)] = personality
    save_system_prompts()
    
    await interaction.response.send_message(
        f"✅ AI personality updated!\n\n**New Personality:**\n{personality[:500]}{'...' if len(personality) > 500 else ''}",
        ephemeral=True
    )

@bot.tree.command(name='get_personality', description='View the current AI personality for this server')
async def get_personality(interaction: discord.Interaction):
    """Show the current system prompt/personality"""
    
    current_prompt = get_system_prompt(interaction.guild.id)
    is_default = current_prompt == DEFAULT_SYSTEM_PROMPT
    
    embed = discord.Embed(
        title="🤖 Current AI Personality",
        description=current_prompt,
        color=0x00ff00 if not is_default else 0x888888
    )
    
    embed.add_field(
        name="Status",
        value="🎭 Custom Personality" if not is_default else "📝 Default Personality",
        inline=True
    )
    
    embed.set_footer(
        text="Use /set_personality to customize (Admin only)" if interaction.user.guild_permissions.manage_guild else "Ask an admin to customize with /set_personality"
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='reset_personality', description='Reset AI personality to default (Admin only)')
async def reset_personality(interaction: discord.Interaction):
    """Reset the system prompt to default"""
    
    # Check if user has manage server permissions
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "❌ You need 'Manage Server' permission to use this command!",
            ephemeral=True
        )
        return
    
    # Reset to default
    if str(interaction.guild.id) in guild_system_prompts:
        del guild_system_prompts[str(interaction.guild.id)]
        save_system_prompts()
    
    await interaction.response.send_message(
        "✅ AI personality reset to default!",
        ephemeral=True
    )

@bot.tree.command(name='clear_memory', description='Clear conversation memory for this channel (Admin only)')
async def clear_memory(interaction: discord.Interaction):
    """Clear the conversation memory for the current channel"""
    
    # Check if user has manage messages permissions
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You need 'Manage Messages' permission to use this command!",
            ephemeral=True
        )
        return
    
    channel_id = interaction.channel.id
    if channel_id in channel_memories:
        del channel_memories[channel_id]
        save_memories()
        await interaction.response.send_message(
            "✅ Conversation memory cleared for this channel!",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "ℹ️ No conversation memory found for this channel.",
            ephemeral=True
        )

@bot.tree.command(name='memory_stats', description='View memory statistics for this channel')
async def memory_stats(interaction: discord.Interaction):
    """Show memory statistics for the current channel"""
    
    channel_id = interaction.channel.id
    
    embed = discord.Embed(
        title="🧠 Memory Statistics",
        color=0x00aaff
    )
    
    if channel_id in channel_memories:
        memories = channel_memories[channel_id]
        total_messages = len(memories)
        
        # Count messages by user
        user_counts = {}
        bot_messages = 0
        
        for memory in memories:
            if memory.is_bot:
                bot_messages += 1
            else:
                user_counts[memory.author_name] = user_counts.get(memory.author_name, 0) + 1
        
        embed.add_field(
            name="Total Messages Remembered",
            value=f"{total_messages}/{MAX_MEMORY_MESSAGES}",
            inline=True
        )
        
        embed.add_field(
            name="Bot Messages",
            value=str(bot_messages),
            inline=True
        )
        
        embed.add_field(
            name="User Messages",
            value=str(total_messages - bot_messages),
            inline=True
        )
        
        if user_counts:
            top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            user_list = '\n'.join([f"{name}: {count}" for name, count in top_users])
            embed.add_field(
                name="Top Contributors",
                value=user_list,
                inline=False
            )
        
        # Show oldest and newest message timestamps
        if memories:
            oldest = min(memories, key=lambda x: x.timestamp)
            newest = max(memories, key=lambda x: x.timestamp)
            
            embed.add_field(
                name="Memory Range",
                value=f"**Oldest:** <t:{int(oldest.timestamp.timestamp())}:R>\n**Newest:** <t:{int(newest.timestamp.timestamp())}:R>",
                inline=False
            )
    
    else:
        embed.add_field(
            name="Memory Status",
            value="No messages remembered for this channel yet.",
            inline=False
        )
    
    embed.set_footer(text=f"Messages expire after {MEMORY_EXPIRY_HOURS} hours")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='ping_ai', description='Test the AI response')
async def ping_ai(interaction: discord.Interaction, message: str = "Hello!"):
    """Test command to ping the AI"""
    
    await interaction.response.defer()
    
    response = await generate_ai_response(
        message, 
        interaction.user.display_name, 
        interaction.guild.id if interaction.guild else 0,
        interaction.channel.id
    )
    
    await interaction.followup.send(f"**You:** {message}\n**AI:** {response}")

# Simple text commands for testing
@bot.command(name='test')
async def test_command(ctx):
    """Simple test command"""
    await ctx.send(f'✅ Bot is working! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='chat')
async def chat_command(ctx, *, message):
    """Chat with the AI via text command"""
    async with ctx.typing():
        response = await generate_ai_response(
            message, 
            ctx.author.display_name, 
            ctx.guild.id if ctx.guild else 0,
            ctx.channel.id
        )
        
        # Store both user message and bot response in memory
        add_message_to_memory(
            ctx.channel.id,
            ctx.author.display_name,
            ctx.author.id,
            message,
            is_bot=False
        )
        
        add_message_to_memory(
            ctx.channel.id,
            bot.user.display_name,
            bot.user.id,
            response,
            is_bot=True
        )
        
        await ctx.reply(response)

# Periodic cleanup task
@bot.event
async def on_ready():
    # Previous on_ready code...
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Connected to {len(bot.guilds)} guild(s)')
    
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')
    
    load_system_prompts()
    load_memories()
    
    try:
        print("Syncing slash commands...")
        synced = await bot.tree.sync()
        print(f'✅ Successfully synced {len(synced)} command(s)')
        for cmd in synced:
            print(f'  - /{cmd.name}: {cmd.description}')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
    
    # Start periodic cleanup task
    bot.loop.create_task(periodic_cleanup())

async def periodic_cleanup():
    """Periodically clean up expired memories and save to disk"""
    while not bot.is_closed():
        try:
            cleanup_expired_memories()
            save_memories()
            print(f"Memory cleanup completed. Active channels: {len(channel_memories)}")
        except Exception as e:
            print(f"Error during periodic cleanup: {e}")
        
        # Wait 1 hour before next cleanup
        await asyncio.sleep(3600)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f'Error: {error}')

if __name__ == '__main__':
    if not TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set!")
        exit(1)
    
    if not OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY not set. AI features will be limited.")
    
    bot.run(TOKEN)