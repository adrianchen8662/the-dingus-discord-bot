import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from openai import OpenAI
import asyncio
import json
import re

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
SITE_URL = os.getenv('SITE_URL', 'https://discord.com')
SITE_NAME = os.getenv('SITE_NAME', 'Discord AI Bot')

# Default system prompt (can be customized per server)
DEFAULT_SYSTEM_PROMPT = """You are the character Kasane Teto. Kasane Teto is officially stated to be 31 years old.[1] However, a popular fan interpretation that she is a teenager stems from one of her earliest and most popular songs, "Kasane Territory ~ Always Teto’s Turn" (in Japanese). The song comedically suggests that because she is a chimera (two halves, one human, forming one being), her age of 31 can be divided in two, making her 15.5 years old. This is a fan-created joke and not her official age, but despite this, the idea entered popular knowledge, leading many to incorrectly assume Teto's "real" age is 15. Teto's developers have acknowledged that fans have differing interpretations of her age and are free to interpret it differently. In her earliest design, she was 159.5 centimetres tall and weighed 47 kilograms. She is listed as liking baguettes (which she is frequently depicted with in fanart) and being a tsundere.[7]

Kasane Teto is portrayed as a youthful girl with reddish hair styled in spiraling twintails resembling drill bits, a style her developers refer to as "twindrills." She typically wears a uniform-style outfit with a red and black color scheme, which has become a recognizable part of her image.

Her personality is generally portrayed as mischievous. """

# Store system prompts per guild
guild_system_prompts = {}

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
    
    # Load saved system prompts
    load_system_prompts()
    
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

def get_system_prompt(guild_id):
    """Get system prompt for a guild"""
    return guild_system_prompts.get(str(guild_id), DEFAULT_SYSTEM_PROMPT)

async def generate_ai_response(message_content, user_name, guild_id, conversation_context=None):
    """Generate AI response using OpenRouter"""
    if not client:
        return "❌ AI service is not configured. Please set up the OPENROUTER_API_KEY."
    
    try:
        # Prepare messages for the conversation
        messages = [
            {"role": "system", "content": get_system_prompt(guild_id)}
        ]
        
        # Add conversation context if provided (for thread conversations)
        if conversation_context:
            messages.extend(conversation_context)
        
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
    # Don't respond to own messages
    if message.author == bot.user:
        return
    
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
            
            # Generate AI response
            response = await generate_ai_response(
                content, 
                message.author.display_name, 
                message.guild.id if message.guild else 0
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

@bot.tree.command(name='ping_ai', description='Test the AI response')
async def ping_ai(interaction: discord.Interaction, message: str = "Hello!"):
    """Test command to ping the AI"""
    
    await interaction.response.defer()
    
    response = await generate_ai_response(
        message, 
        interaction.user.display_name, 
        interaction.guild.id if interaction.guild else 0
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
            ctx.guild.id if ctx.guild else 0
        )
        await ctx.reply(response)

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