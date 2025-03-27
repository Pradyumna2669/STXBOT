import discord
import json
import os
from discord.ext import commands, tasks
from discord import app_commands, utils
from discord.ui import Select, Button, View, Modal, TextInput
from datetime import datetime, timedelta
import asyncio
import requests
import logging
import base64
import re
import aiohttp
import io
import psutil
import pytz
from jinja2 import Template, Environment, BaseLoader
from dotenv import load_dotenv
load_dotenv()
DATA_FILE = "channels.json"
TICKETS_FILE = "tickets.json"
TICKET_COUNTER_FILE = "ticket_counter.txt"
TICKET_CREATION_MESSAGE_FILE = "ticket_creation_message_id.txt"
pseudo_mod_list = []  # List of users to be approved for pseudo-mod role
mod_promotion_list = []  # List of pseudo-mods to be promoted to full mods
MUTE_ROLE_ID = '5674654546746756'
WARNINGS_FILE = 'warnings.json'
# File to store monitored VC IDs persistently
MONITORED_VC_FILE = "monitored_vcs.json"
MONITORED_VC_IDS = set()  # Ensure it's globally declared
tickets = {}
ticket_counter = 0
TICKET_CREATION_MESSAGE_ID = None
# Load warnings from the JSON file
# Load existing data from file
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ticket Transcript</title>
    <link rel="stylesheet" href="https://Pradyumna2669.github.io/discord-ticket-transcripts/transcripts/transcript.css">
</head>
<body>
    <div class="discord-chat">
        <!-- Chat Header -->
        <div class="chat-header">
            <span class="channel-name">#ticket-{{ ticket_id }}</span>
            <span class="channel-description">Welcome to #ticket-{{ ticket_id }}! This is the start of the #ticket-{{ ticket_id }} channel.</span>
        </div>

        <!-- Messages Container -->
        <div class="messages">
            {% for message in messages %}
            <div class="message">
                <!-- Author Section (with PFP and Role Color) -->
                <div class="author">
                    <img src="{{ message.author_avatar }}" alt="PFP" class="avatar">
                    <span class="username" style="color: {{ message.author_role_color }};">{{ message.author }}</span>
                    <span class="timestamp">{{ message.timestamp }}</span>
                </div>

                <!-- Message Content -->
                <div class="content">
                    {{ message.content | replace_mentions(users) }}
                </div>

                <!-- Embeds (if any) -->
                {% if message.embeds %}
                <div class="embeds">
                    {% for embed in message.embeds %}
                    <div class="embed">
                        <div class="embed-color" style="background-color: {{ embed.color }};"></div>
                        <div class="embed-content">
                            {% if embed.title %}
                            <div class="embed-title">{{ embed.title }}</div>
                            {% endif %}
                            {% if embed.description %}
                            <div class="embed-description">{{ embed.description }}</div>
                            {% endif %}
                            {% if embed.fields %}
                            <div class="embed-fields">
                                {% for field in embed.fields %}
                                <div class="embed-field">
                                    <span class="field-name">{{ field.name }}</span>
                                    <span class="field-value">{{ field.value }}</span>
                                </div>
                                {% endfor %}
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Save data to file
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

CHANNELS = load_data()
def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save warnings to the JSON file
def save_warnings(warnings):
    with open(WARNINGS_FILE, 'w') as f:
        json.dump(warnings, f)

# Ticket system all loads and save section
def load_tickets():
    """Load ticket data from a file."""
    global tickets
    if os.path.exists(TICKETS_FILE):
        try:
            with open(TICKETS_FILE, "r") as f:
                tickets = json.load(f)
        except json.JSONDecodeError:
            print("tickets.json is empty or contains invalid JSON. Initializing with an empty dictionary.")
            tickets = {}
    else:
        print("tickets.json does not exist. Initializing with an empty dictionary.")
        tickets = {}

# Save ticket data to file
def save_tickets():
    """Save ticket data to a file."""
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=4)

# Load ticket counter from file
def load_ticket_counter():
    """Load the ticket counter from a file."""
    global ticket_counter
    if os.path.exists(TICKET_COUNTER_FILE):
        with open(TICKET_COUNTER_FILE, "r") as f:
            ticket_counter = int(f.read().strip())
    else:
        ticket_counter = 0

# Save ticket counter to file
def save_ticket_counter():
    """Save the ticket counter to a file."""
    with open(TICKET_COUNTER_FILE, "w") as f:
        f.write(str(ticket_counter))

# Load ticket creation message ID from file
def load_ticket_creation_message_id():
    """Load the ticket creation message ID from a file."""
    global TICKET_CREATION_MESSAGE_ID
    if os.path.exists(TICKET_CREATION_MESSAGE_FILE):
        with open(TICKET_CREATION_MESSAGE_FILE, "r") as f:
            TICKET_CREATION_MESSAGE_ID = int(f.read().strip())
    else:
        TICKET_CREATION_MESSAGE_ID = None

# Save ticket creation message ID to file
def save_ticket_creation_message_id():
    """Save the ticket creation message ID to a file."""
    with open(TICKET_CREATION_MESSAGE_FILE, "w") as f:
        f.write(str(TICKET_CREATION_MESSAGE_ID))
from jinja2 import Environment, BaseLoader

# Define the custom filter
def replace_mentions_filter(content, users):
    """Replace user mentions in the message content with their usernames."""
    for user_id, username in users.items():
        content = content.replace(f"<@{user_id}>", f"@{username}")
        content = content.replace(f"<@!{user_id}>", f"@{username}")  # Handle nicknames
    return content

# Create a Jinja2 environment with the custom filter
env = Environment(loader=BaseLoader)
env.filters['replace_mentions'] = replace_mentions_filter

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create file handler to save logs to a file
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.INFO)

# Create a formatter and set it for the file handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

# Load monitored VCs from file
def load_monitored_vcs():
    """Load the monitored VC IDs from a file."""
    global MONITORED_VC_IDS
    try:
        with open("monitored_vcs.json", "r") as f:
            MONITORED_VC_IDS = set(json.load(f))  # Convert list back to set
    except (FileNotFoundError, json.JSONDecodeError):
        MONITORED_VC_IDS = set()

# Save monitored VCs to file
def save_monitored_vcs():
    """Save the monitored VC IDs to a file."""
    with open("monitored_vcs.json", "w") as f:
        json.dump(list(MONITORED_VC_IDS), f)  # Convert set to list for JSON storage

# Load initial monitored VCs
MONITORED_VC_IDS = load_monitored_vcs()
    
# Your Discord bot setup
GUILD_ID = 4644654346354453
AFK_VC_ID = 43435124652626424
TOKEN = 'etzsgdxzffhxdt65h41dt65h1d51yty'  # Use environment variables for sensitive data
ROLE_ID = 67654567875872873755  # Role to assign for compliant users
ABUSE_LOG_CHANNEL_ID = 77567867867676  # Replace with your actual abuse log channel ID
MOD_LOG_CHANNEL_ID = 7867886786786786
MUTE_ROLE_ID = 787676798867867896786  # Replace with your actual Muted role ID
MORNING_GRIND_ROLE_ID = 786788678867886786786  # Replace with your actual Morning Grind role ID
AFTERNOON_GRIND_ROLE_ID = 786786786786786786  # Replace with your actual Afternoon Grind role ID
EVENING_GRIND_ROLE_ID = 78867889676786786786  # Replace with your actual Eve-Night Grind role ID
PSEUDO_MOD_ROLE_ID = 7867867867869786786  # Replace with actual role ID
MOD_ROLE_ID = 786786786786786867  # Replace with your actual Moderator role ID
ELDER_ROLE_ID = 7678676786786756  # Replace with your actual Elder role ID
STAFF_ROLE_ID = 767867867867678676
ADMIN_ROLE_ID = 78678678678677837
TICKET_CREATION_CHANNEL_ID = 7678678672872723752
TRANSCRIPTS_CHANNEL_ID = 737645324556484832453
TICKET_CATEGORY_ID = 673786345378678567563
SUPPORT_ROLE_ID = 7867675532786737563793
BOT_ROLE_ID = 76373782786745645645  # Replace with your actual bot role ID
GITHUB_TOKEN = "dgsdrtstsetbwst516841se541s"


# List of NSFW keywords (add your words here)
NSFW_KEYWORDS = [
    "cock", "deepthroat", "dick", "cumshot", "fuck", "sperm",
    "jerk off", "naked", "ass", "tits", "fingering", "masturbate",
    "bitch", "blowjob", "prostitute", "bullshit", "dumbass",
    "dickhead", "pussy", "piss", "asshole", "boobs", "booty",
    "dildo", "erection", "foreskin", "gag", "handjob", "licking",
    "nude", "penis", "porn", "vibrator", "viagra", "virgin",
    "vagina", "vulva", "wet dream", "threesome", "orgy", "bdsm",
    "hickey", "condom", "sexting", "squirt", "testicles", "anal",
    "bareback", "bukkake", "creampie", "stripper", "strap-on",
    "clitoris", "cock ring", "sugar daddy", "cowgirl", "reach-around",
    "doggy style", "makeup sex", "lingerie", "butt plug", "moan",
    "milf", "wank", "oral", "sucking", "dirty talk", "straddle",
    "bondage", "orgasm", "scissoring", "deeper", "slut", "cumming",
    "jerk", "prick", "cunt", "bastard", "faggot", "sex", "asshole", "I'll teach 10people to earn", "interested people should apply", "I'll teach to earn", "steam gift", "telegram or whatsapp", "looking to help", "https://discord.gg/", "rape"
]
# Role IDs allowed to use commands
ALLOWED_ROLE_IDS = [1121001670596378725, 1120673829350555698, 1080695859093717043, 1316094443677290548, 1175697980054057000]  # Replace with actual role IDs

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.reactions = True
intents.members = True
intents.messages = True  # This is crucial for the bot to read messages
intents.message_content = True  # Enable the message content intent

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
user_warnings = load_warnings()  # Load warnings when the bot starts

user_compliance = {}
applications = {}

def has_allowed_role():
    async def predicate(ctx):
        return any(role.id in ALLOWED_ROLE_IDS for role in ctx.author.roles)
    return commands.check(predicate)

def is_bot_user(member):
    """Check if member has the bot role (for pseudo-bot accounts)"""
    return any(role.id == BOT_ROLE_ID for role in member.roles)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    load_monitored_vcs()  # Load monitored VCs on startup
    await bot.tree.sync()  # Ensure slash commands are registered
        # Remove the specified role from all members in the guild
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        logger.warning("Guild not found!")
        return
    
    if guild:
        for vc_id in MONITORED_VC_IDS:
            vc = guild.get_channel(vc_id)
            if vc and isinstance(vc, discord.VoiceChannel):
                for member in vc.members:
                    user_compliance[member.id] = {'warn_count': 0, 'monitoring': True}
                    await check_compliance_status(member)
    if not check_compliance.is_running():
        check_compliance.start()  # Start compliance checks

    role_to_remove = guild.get_role(ROLE_ID)
    if role_to_remove is None:
        logger.warning(f"Role with ID {ROLE_ID} not found.")
        return

    # Iterate through all members and remove the role if they have it
    for member in guild.members:
        if role_to_remove in member.roles:
            try:
                await member.remove_roles(role_to_remove)
                logger.info(f"Removed role {role_to_remove.name} from {member.name}.")
            except discord.Forbidden:
                logger.warning(f"Unable to remove role from {member.name}. Missing permissions.")
    
    load_ticket_counter()
    load_ticket_creation_message_id()
    load_tickets()  # Load ticket data on startup
    await setup_ticket_creation_message()
    await reattach_ticket_views()  # Reattach views to existing tickets
    await update_channel_names()
    scheduled_update.start()            

MONITORED_VC_IDS = set()  # Ensure it's always a set

@bot.event
async def on_voice_state_update(member, before, after):
    if is_bot_user(member):  # Changed from member.bot
        return
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_ID)
    if after.channel and after.channel.id in MONITORED_VC_IDS:  # User joins a monitored VC
        if before.channel is None or before.channel.id not in MONITORED_VC_IDS:
            # Start compliance monitoring
            user_compliance[member.id] = {'warn_count': 0, 'monitoring': True}
            await check_compliance_status(member)  # Immediate check
            asyncio.create_task(schedule_compliance_check(member))  # Start timed check

    if before.channel and before.channel.id in MONITORED_VC_IDS and after.channel is None:
        # User left monitored VC, remove from tracking
        user_compliance.pop(member.id, None)

     # Check if the user is in any voice channel
    if after.channel:
        # If the user starts streaming or turns on the camera
        if member.voice.self_stream or member.voice.self_video:
            if role not in member.roles:
                try:
                    await member.add_roles(role)
                    logger.info(f"Added role {role.name} to {member.name} for using camera/screen share.")
                except discord.Forbidden:
                    logger.warning(f"Unable to add role to {member.name}. Missing permissions.")

        # If the user stops streaming or turns off the camera
        elif role in member.roles:
            try:
                await member.remove_roles(role)
                logger.info(f"Removed role {role.name} from {member.name} as they stopped sharing.")
            except discord.Forbidden:
                logger.warning(f"Unable to remove role from {member.name}. Missing permissions.")

    # If the user leaves the voice channel, remove the role
    elif before.channel and role in member.roles:
        try:
            await member.remove_roles(role)
            logger.info(f"Removed role {role.name} from {member.name} as they left VC.")
        except discord.Forbidden:
            logger.warning(f"Unable to remove role from {member.name}. Missing permissions.")
        
async def schedule_compliance_check(member):
    """Schedules compliance check every 1 minute if user is still non-compliant"""
    await asyncio.sleep(60)
    if member.id in user_compliance and user_compliance[member.id]['monitoring']:
        await check_compliance_status(member)

async def check_compliance_status(member):
    """Checks if a member is complying and takes action if not"""
    if is_bot_user(member):  # Changed from member.bot
        return
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_ID)

    if member.voice and member.voice.channel and member.voice.channel.id in MONITORED_VC_IDS:
        if not (member.voice.self_stream or member.voice.self_video):
            user_compliance[member.id]['warn_count'] += 1
            warn_count = user_compliance[member.id]['warn_count']

            if warn_count == 1:
                await send_warning(member, "First warning: Please Turn on your camera or share your screen within 1 minute.")
            elif warn_count == 2:
                await send_warning(member, "Final warning: Turn on your camera or you will be moved to AFK.")
            elif warn_count >= 3:
                await move_to_afk(member)
        else:
            user_compliance[member.id]['warn_count'] = 0  # Reset if they comply
    else:
        user_compliance.pop(member.id, None)
        if role in member.roles:
            await member.remove_roles(role)

@tasks.loop(seconds=60)
async def check_compliance():
    """Periodically checks compliance for all monitored users"""
    if is_bot_user(member):  # Changed from member.bot
        return
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_ID)

    for user_id, status in list(user_compliance.items()):
        member = guild.get_member(user_id)
        if member:
            if member.voice and member.voice.channel and member.voice.channel.id in MONITORED_VC_IDS:
                if not (member.voice.self_stream or member.voice.self_video):
                    status['warn_count'] += 1
                    if status['warn_count'] == 1:
                        await send_warning(member, "First warning: Please turn on your camera or share your screen.")
                    elif status['warn_count'] == 2:
                        await send_warning(member, "Final warning: Turn on your camera or you will be moved to AFK.")
                    elif status['warn_count'] >= 3:
                        await move_to_afk(member)
                else:
                    status['warn_count'] = 0  # Reset if they comply
                    await member.add_roles(role)
            else:
                user_compliance.pop(user_id, None)
                if role in member.roles:
                    await member.remove_roles(role)

async def send_warning(member, message):
    """Sends a warning message to the user via DM"""
    try:
        await member.send(message)
        print(f"Warning sent to {member.name}.")
    except discord.Forbidden:
        print(f"Unable to DM {member.name}. Possibly disabled DMs.")

async def move_to_afk(member):
    """Moves the user to AFK channel if they fail compliance"""
    afk_channel = bot.get_channel(AFK_VC_ID)
    if afk_channel:
        await member.move_to(afk_channel)
        print(f"{member.name} moved to AFK channel due to non-compliance.")

async def check_nsfw_content(message):
    """Check if the message contains NSFW content."""
    return any(re.search(r'\b' + re.escape(keyword) + r'\b', message.content, re.IGNORECASE) for keyword in NSFW_KEYWORDS)

async def handle_nsfw_message(message, keyword):
    # Mute the user
    mute_role = discord.utils.get(message.guild.roles, id=MUTE_ROLE_ID)
    await message.author.add_roles(mute_role)
    
    # Prepare the embed for the abuse log
    content = message.content[:1020]  # Truncate content to 1020 characters
    jump_url = message.jump_url  # Get the URL to jump to the original message
    embed = discord.Embed(
        title="NSFW Content Detected",
        description=f"{message.author.mention} posted NSFW content.",
        color=discord.Color.red()
    )
    embed.add_field(name="Message Content", value=content)
    embed.add_field(name="Keyword", value=keyword)
    embed.add_field(name="Action Taken", value="Muted")
    embed.add_field(name="Jump to Message", value=f"[Click here]({jump_url})")
    embed.set_footer(text="Please adhere to the server rules.")

    # Send to abuse-log channel
    abuse_log_channel = message.guild.get_channel(ABUSE_LOG_CHANNEL_ID)
    if abuse_log_channel:
        await abuse_log_channel.send(embed=embed)

    # Notify the user
    user_embed = discord.Embed(
        title="Warning: NSFW Content",
        description="You have been muted for posting NSFW content.",
        color=discord.Color.orange()
    )
    user_embed.add_field(name="Your Message", value=content)
    user_embed.add_field(name="Keyword Detected", value=keyword)
    await message.author.send(embed=user_embed)

    # Log the action in the mod log channel
    mod_log_channel = message.guild.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_log_channel:
        await mod_log_channel.send(embed=embed)
    
    # Delete the original message
    await message.delete()
        
@bot.event
async def on_message(message):
    # If the message is in DMs, process commands and return
    if isinstance(message.channel, discord.DMChannel):  # If the message is in DMs
        await bot.process_commands(message)  # Allow processing commands in DMs
        return

    # Process commands for server messages
    await bot.process_commands(message)

    # Check for NSFW keywords in the message
    if await check_nsfw_content(message):
        for keyword in NSFW_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword) + r'\b', message.content, re.IGNORECASE):
                await handle_nsfw_message(message, keyword)
                return

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    raise error  # Raise other errors for debugging

@bot.tree.command(name="monitor_vc", description="Add Cam Monitoring VC")
@app_commands.describe(action="add, remove, or list", vc="Voice channel to modify")
async def monitor_vc(interaction: discord.Interaction, action: str, vc: discord.VoiceChannel = None):
    """Manage monitored voice channels dynamically."""
    global MONITORED_VC_IDS

    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)

    action = action.lower()
    if action == "add":
        if vc:
            MONITORED_VC_IDS.add(vc.id)
            save_monitored_vcs()
            
            # Check all current members in the VC
            for member in vc.members:
                if member.id not in user_compliance:
                    user_compliance[member.id] = {'warn_count': 0, 'monitoring': True}
                    await check_compliance_status(member)
                    asyncio.create_task(schedule_compliance_check(member))
            
            response_message = f"✅ Added **{vc.name}** to monitored VCs and checking current members."
        else:
            response_message = "❌ Please mention a valid voice channel."
    elif action == "remove":
        if vc and vc.id in MONITORED_VC_IDS:
            MONITORED_VC_IDS.remove(vc.id)
            save_monitored_vcs()
            
            # Remove compliance tracking for members in this VC
            for member in vc.members:
                if member.id in user_compliance:
                    user_compliance.pop(member.id, None)
            
            response_message = f"✅ Removed **{vc.name}** from monitored VCs."
        else:
            response_message = "❌ This channel is not in the monitored list."
    elif action == "list":
        if MONITORED_VC_IDS:
            vc_list = "\n".join([f"<#{vc_id}>" for vc_id in MONITORED_VC_IDS])
            response_message = f"📢 **Monitored VCs:**\n{vc_list}"
        else:
            response_message = "❌ No monitored VCs."
    else:
        response_message = "❌ Invalid action. Use `add`, `remove`, or `list`."

    await interaction.followup.send(response_message, ephemeral=(action != "list"))  

@bot.tree.command(name="add_pseudo_mod", description="Add Pseudo Mod in List")
@app_commands.describe(member="The member to add to the pseudo-mod list")
async def add_pseudo_mod(interaction: discord.Interaction, member: discord.Member):
    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)
        
    if member.id not in pseudo_mod_list:
        pseudo_mod_list.append(member.id)
        await interaction.followup.send(f"{member.mention} has been added to the pseudo-mod approval list.", ephemeral=True)
    else:
        await interaction.followup.send(f"{member.mention} is already in the pseudo-mod approval list.")

@bot.tree.command(name="approve_pseudo_mods", description="Approve Pseudo Moderator List")
async def approve_pseudo_mods(interaction: discord.Interaction):
    
    guild = interaction.guild
    role = guild.get_role(PSEUDO_MOD_ROLE_ID)
    
    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)
        
    if not role:
        await interaction.response.send_message("Pseudo-Mod role not found!", ephemeral=True)
        return
    
    for member_id in pseudo_mod_list:
        member = guild.get_member(member_id)
        if member:
            await member.add_roles(role)
            embed = discord.Embed(
                title="Pseudo MOD Rules",
                description=f"Welcome to the team {member.mention}.",
                color=discord.Color.blue()  # You can change the color
            )
            embed.add_field(
                name="1. **Server Rules**",
                value="Go to this chat https://discord.com/channels/1063837473219813440/1076407384416727101/1076410421738741760 .",
                inline=False
            )

            embed.add_field(
                name="2. **Follow these Rules (PSEUDO/MOD RULES):**",
                value="Go to this chat https://discord.com/channels/1063837473219813440/1151622302010708078/1161642312091316314 .",
                inline=False
            )
            embed.add_field(
                name="4. **General Staff Rules**",
                value="Go to this chat https://discord.com/channels/1063837473219813440/1151622302010708078/1220438028795908146 .",
                inline=False
            )
            embed.add_field(
                name="3. **Use of commands**",
                value="Go to this chat https://discord.com/channels/1063837473219813440/1151622302010708078/1347850986030632992 .",
                inline=False
            )
            embed.set_footer(text="STOIC TEAM")
            await member.send(embed=embed)
    
    pseudo_mod_list.clear()  # Clear the list after approval
    await interaction.followup.send("All pseudo-mods have been approved.")

@bot.tree.command(name="add_mod", description="Add Mod in Moderator List")
@app_commands.describe(member="The member to add to the mod promotion list")
async def add_mod(interaction: discord.Interaction, member: discord.Member):
    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)
        
    if member.id not in mod_promotion_list:
        mod_promotion_list.append(member.id)
        await interaction.followup.send(f"{member.mention} has been added to the mod promotion list.")
    else:
        await interaction.followup.send(f"{member.mention} is already in the mod promotion list.")

@bot.tree.command(name="approve_mods", description="Approve the Mods List")
async def approve_mods(interaction: discord.Interaction):
    guild = interaction.guild
    pseudo_role = guild.get_role(PSEUDO_MOD_ROLE_ID)
    mod_role = guild.get_role(MOD_ROLE_ID)

    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)
        
    if not mod_role:
        await interaction.followup.send("Mod role not found!", ephemeral=True)
        return

    for member_id in mod_promotion_list:
        member = guild.get_member(member_id)
        if member:
            if pseudo_role:
                await member.remove_roles(pseudo_role)
            await member.add_roles(mod_role)
            await member.send(f"{member.mention} has been promoted to **Moderator**! 🎉")
    
    mod_promotion_list.clear()  # Clear the list after approval
    await interaction.response.send_message("All moderators have been approved.")

@bot.tree.command(name="view_list")
@app_commands.describe(list_name="The name of the list to view: 'pseudo_mod' or 'mod'")
async def view_list(interaction: discord.Interaction, list_name: str):
    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)
        
    if list_name.lower() == "pseudo_mod":
        members = [f"<@{member_id}>" for member_id in pseudo_mod_list]
        message = "Pseudo-Mod Approval List: " + (", ".join(members) if members else "No members in the list.")
    elif list_name.lower() == "mod":
        members = [f"<@{member_id}>" for member_id in mod_promotion_list]
        message = "Mod Promotion List: " + (", ".join(members) if members else "No members in the list.")
    else:
        message = "Invalid list name. Use 'pseudo_mod' or 'mod'."
    
    await interaction.followup.send(message)        

@bot.command()
@has_allowed_role()
async def unmute(ctx, member: discord.Member = None):
    """Unmute a member and log the action."""
    if member is None:
        await ctx.send("Please specify a member to unmute. Usage: `!unmute @username`.")
        return
    
    mute_role = discord.utils.get(ctx.guild.roles, id=MUTE_ROLE_ID)
    if mute_role in member.roles:
        await member.remove_roles(mute_role)

        # Prepare the embed for mod-log
        embed = discord.Embed(
            title="Member Unmuted",
            description=f"{member.mention} has been unmuted.",
            color=discord.Color.green()  # You can choose any color you like
        )
        embed.add_field(name="Unmuted by", value=ctx.author.mention)
        embed.set_footer(text="Action taken.")

        # Send to mod-log channel
        mod_log_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_log_channel:
            await mod_log_channel.send(embed=embed)

        # Send confirmation embed back to the user
        user_embed = discord.Embed(
            title="Unmute Confirmation",
            description=f"{member.mention} has been successfully unmuted.",
            color=discord.Color.green()
        )
        user_embed.add_field(name="Action Taken By", value=ctx.author.mention)
        await ctx.send(embed=user_embed)

    else:
        await ctx.send(f"{member.mention} is not muted.")

@bot.command()
@has_allowed_role()  
async def health(ctx):
    # Get system metrics
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')
    cpu_temp = os.popen('vcgencmd measure_temp').readline().strip()

    # Create an embed message
    embed = discord.Embed(title="Server Health", color=discord.Color.blue())
    embed.add_field(name="CPU Usage", value=f"{cpu_usage}%", inline=False)
    embed.add_field(name="Memory Usage", value=f"{memory_info.percent}%", inline=False)
    embed.add_field(name="Disk Usage", value=f"{disk_usage.percent}%", inline=False)
    embed.add_field(name="CPU Temperature", value=cpu_temp, inline=False)

    # Send the embed message
    await ctx.send(embed=embed)

@bot.command(name="pingvc")
async def ping_vc_members(ctx):
    # Try to get the VC from the user first
    if ctx.author.voice:
        voice_channel = ctx.author.voice.channel
    else:
        # Fallback: Try to find a VC matching the text channel's name
        voice_channel = discord.utils.get(ctx.guild.voice_channels, name=ctx.channel.name)
        
        if not voice_channel:
            return await ctx.send("❌ Could not find a linked voice channel!")

    members = voice_channel.members
    if not members:
        return await ctx.send("🔇 No one is in this voice channel!")
    
    mentions = [m.mention for m in members if not m.bot]
    await ctx.send(f"📢 **Pinging VC Members:** {' '.join(mentions)}")

@bot.command()
@has_allowed_role()  # Replace with your role check decorator
async def warn(ctx, member: discord.Member, *, reason: str = "No reason specified."):
    """Warn a member with an optional reason."""
    user_id = str(member.id)
    
    # Increment the warning count
    if user_id in user_warnings:
        user_warnings[user_id] += 1
    else:
        user_warnings[user_id] = 1

    # Prepare the embed for mod-log
    embed = discord.Embed(
        title="Warning Issued",
        description=f"{member.mention} has been warned.",
        color=discord.Color.red()  # Change color as needed
    )
    embed.add_field(name="Total Warnings", value=user_warnings[user_id])
    embed.add_field(name="Issued by", value=ctx.author.mention)
    embed.add_field(name="Reason", value=reason)
    embed.set_footer(text="Please adhere to the server rules.")

    # Send to mod-log channel
    mod_log_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_log_channel:
        await mod_log_channel.send(embed=embed)

    # Notify the user (with error handling for DMs)
    user_embed = discord.Embed(
        title="Warning Notification",
        description=f"You have received a warning. Total warnings: {user_warnings[user_id]}",
        color=discord.Color.yellow()  # Different color for user notification
    )
    user_embed.add_field(name="Reason", value=reason)
    
    try:
        await member.send(embed=user_embed)
    except discord.Forbidden:
        # If DMs are disabled, send a message in the channel
        await ctx.send(f"{member.mention}, you've been warned but I couldn't DM you. Please enable DMs to receive warnings privately.")
        # Also send the warning details in the channel (visible to moderators)
        await ctx.send(embed=user_embed)

    # Check if the user has reached the warning limit
    if user_warnings[user_id] >= 5:
        mute_role = discord.utils.get(ctx.guild.roles, id=MUTE_ROLE_ID)
        if mute_role:
            await member.add_roles(mute_role)
            await ctx.send(f"{member.mention} has been muted for reaching the warning limit of 5.")
            logger.info(f"{member.name} has been muted for reaching 5 warnings.")
        
        # Reset the user's warning count
        user_warnings.pop(user_id, None)

    # Save updated warnings
    save_warnings(user_warnings)

    # Short embed response back to the command issuer
    response_embed = discord.Embed(
        title="Warning Issued",
        description=f"{member.mention} has been warned successfully.",
        color=discord.Color.green()  # Green color for success
    )
    response_embed.add_field(name="Reason", value=reason)
    await ctx.send(embed=response_embed)

@bot.command()
@has_allowed_role()  # Ensure the user has the allowed role
async def mute(ctx, member: discord.Member, *, reason: str = "No reason specified."):
    """Mute a member and log the action."""
    mute_role = discord.utils.get(ctx.guild.roles, id=MUTE_ROLE_ID)
    
    if mute_role is None:
        await ctx.send("Mute role not found. Please check the role ID.")
        return

    if mute_role in member.roles:
        await ctx.send(f"{member.mention} is already muted.")
        return
    
    await member.add_roles(mute_role)
    await member.move_to(None)
    # Prepare the embed for mod-log
    embed = discord.Embed(
        title="Member Muted",
        description=f"{member.mention} has been muted.",
        color=discord.Color.red()  # You can choose any color you like
    )
    embed.add_field(name="Muted by", value=ctx.author.mention)
    embed.add_field(name="Reason", value=reason)
    embed.set_footer(text="Action taken.")

    # Send to mod-log channel
    mod_log_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_log_channel:
        await mod_log_channel.send(embed=embed)

    await ctx.send(f"{member.mention} has been muted for: {reason}.")    
    
@bot.command()
@has_allowed_role()  # Replace with your role check decorator
async def warnings(ctx, member: discord.Member):
    """Check the number of warnings for a member."""
    user_id = str(member.id)
    count = user_warnings.get(user_id, 0)

    # Prepare the embed
    embed = discord.Embed(
        title="Warning Count",
        description=f"{member.mention} has {count} warnings.",
        color=discord.Color.blue()  # Change color as needed
    )
    embed.add_field(name="User ID", value=user_id)
    embed.set_footer(text="Use this information responsibly.")

    # Send the embed message
    await ctx.send(embed=embed)
    
@bot.command(name='del_warn')
@has_allowed_role()  # Ensure the user has the allowed role
async def del_warn(ctx, member: discord.Member, count: int = 1):
    """Delete a specified number of warnings for a member."""
    user_id = str(member.id)

    # Check if the user has any warnings
    if user_id not in user_warnings or user_warnings[user_id] <= 0:
        await ctx.send(f"{member.mention} has no warnings to delete.")
        return

    # Decrease the warning count, ensuring it doesn't go below zero
    user_warnings[user_id] = max(user_warnings[user_id] - count, 0)

    # Prepare the embed for mod-log
    embed = discord.Embed(
        title="Warning Deleted",
        description=f"{count} warning(s) deleted for {member.mention}.",
        color=discord.Color.green()
    )
    embed.add_field(name="Remaining Warnings", value=user_warnings[user_id])
    embed.add_field(name="Updated by", value=ctx.author.mention)
    embed.set_footer(text="Please adhere to the server rules.")

    # Send to mod-log channel
    mod_log_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_log_channel:
        await mod_log_channel.send(embed=embed)

    # Notify the user
    user_embed = discord.Embed(
        title="Warning Update",
        description=f"You have had {count} warning(s) removed.",
        color=discord.Color.blue()
    )
    user_embed.add_field(name="Remaining Warnings", value=user_warnings[user_id])
    await member.send(embed=user_embed)

    # Save updated warnings
    save_warnings(user_warnings)

    await ctx.send(f"{count} warning(s) deleted for {member.mention}.")
    
@bot.command()
@has_allowed_role()  # Ensure the user has the allowed role
async def apologize(ctx):
    """Send an official apology message from the bot."""
    # Prepare the apology embed
    embed = discord.Embed(
        title="Official Apology",
        description="I sincerely apologize for any inconvenience caused to the you and community.",
        color=discord.Color.blue()  # You can choose any color you like
    )
    embed.set_footer(text="This message is sent by the bot.")

    # Send the embed in the same channel
    await ctx.send(embed=embed)

@bot.command(name='rule')
@has_allowed_role()  # Ensure the user has the allowed role (you can adjust the permission check as needed)
async def rule(ctx):
    """Send the study rules in a professional and cool embed."""
    
    embed = discord.Embed(
        title="Study Room Rules 📚",
        description="Please adhere to the following rules to maintain a smooth and productive environment.",
        color=discord.Color.blue()  # You can change the color if you want something more vibrant or subdued
    )

    # Adding rules to the embed
    embed.add_field(
        name="1️⃣ DO CAM OR SCREEN SHARE TO AVOID GETTING THROWN OUT",
        value="To maintain a productive study environment, please turn on your camera or start screen sharing. If not, you risk being moved to AFK.",
        inline=False
    )
    
    embed.add_field(
        name="2️⃣ ALLOWED COMMANDS INCLUDE `/POMODORO`, `/LIST`, AND MORE",
        value="Feel free to use study-related commands such as `/pomodoro` or `/list` to manage your tasks and stay productive. Other commands may be restricted.",
        inline=False
    )
    
    embed.add_field(
        name="3️⃣ MAINTAIN A SAFE STUDY ENVIRONMENT",
        value="Respect others and maintain a safe, quiet, and focused atmosphere for everyone. No disruptive behavior is allowed.",
        inline=False
    )
    
    # Optional footer
    embed.set_footer(text="Thank you for your cooperation! 🙏")

    # Send the embed to the same channel
    await ctx.send(embed=embed)    
    
# Check if the user has admin permissions
def is_admin(ctx):
    return any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)
                    
@bot.command()
async def send_dm(ctx, member: discord.Member, *, message: str):
    """Send a DM to a user."""
    try:
        # Send the message to the member via DM
        await member.send(message)
        await ctx.send(f"Sent a DM to {member.mention}.")
    except discord.Forbidden:
        # Handle the case where the bot can't send a DM (user has DMs disabled)
        await ctx.send(f"Could not send a DM to {member.mention}. They may have DMs disabled.")
    except discord.HTTPException as e:
        # Handle any other HTTP errors
        await ctx.send(f"An error occurred while sending the DM: {e}")                    

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    await ctx.send(f"Pong! Latency: {latency}ms")

@bot.command()
async def send_invwarn(ctx, member: discord.Member):
    """Send a warning about unauthorized server invite in an embed."""
    
    # Create an embed with the warning message
    embed = discord.Embed(
        title="⚠️ Warning: Unauthorized Server Invitation",
        description=(
            "We have received a complaint that you shared an invite link to another server. "
            "Please note that this behavior is against the rules of this server. If such complaints are "
            "received again, further action will be taken, which may include a ban.\n\n"
            "We ask you to kindly refrain from sharing any external invites and respect the guidelines of this community.\n\n"
            "Thank you for your cooperation."
        ),
        color=discord.Color.orange()  # You can choose a different color if you'd like
    )
    embed.set_footer(text=f"Message from {ctx.author}")  # Footer shows who sent the message
    
    try:
        # Send the embed to the user via DM
        await member.send(embed=embed)
        await ctx.send(f"Sent a invite warning to {member.mention}.")
    except discord.Forbidden:
        # Handle the case where the bot can't send a DM (user has DMs disabled)
        await ctx.send(f"Could not send a DM to {member.mention}. They may have DMs disabled.")
    except discord.HTTPException as e:
        # Handle any other HTTP errors
        await ctx.send(f"An error occurred while sending the DM: {e}")        
        
# Command: !send_message channelid message [attachment]
@bot.command()
async def send_message(ctx, channel_id: int, *, message: str):
    """Sends the specified message and optionally an attachment to the given channel."""
    # Try to get the channel by ID
    channel = bot.get_channel(channel_id)

    if not channel:
        await ctx.send(f"Couldn't find channel with ID: {channel_id}")
        return

    # Check if the channel belongs to the guild
    if channel.guild != ctx.guild:
        await ctx.send("The specified channel does not belong to this guild.")
        return

    # Check if the user has permission to send messages in the channel
    if not channel.permissions_for(ctx.author).send_messages:
        await ctx.send("You do not have permission to send messages in that channel.")
        return

    # Check if the bot has permission to send messages in the channel
    if not channel.permissions_for(ctx.guild.me).send_messages:
        await ctx.send("I do not have permission to send messages in that channel.")
        return

    # Check if there is an attachment in the message
    attachment = None
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]

    # If it's a TextChannel, send the message (and attachment if available)
    if isinstance(channel, discord.TextChannel):
        if attachment:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as response:
                        if response.status == 200:
                            with io.BytesIO(await response.read()) as file:
                                file.seek(0)
                                await channel.send(message, file=discord.File(file, attachment.filename))
                        else:
                            await channel.send(f"Failed to download attachment from {attachment.url}")
            except Exception as e:
                await ctx.send(f"An error occurred while downloading the attachment: {e}")
        else:
            await channel.send(message)

    # If it's a VoiceChannel, send the message to the mod log channel
    elif isinstance(channel, discord.VoiceChannel):
        text_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
        if not text_channel:
            await ctx.send("Could not find the mod log channel.")
            return

        if attachment:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as response:
                        if response.status == 200:
                            with io.BytesIO(await response.read()) as file:
                                file.seek(0)
                                await text_channel.send(f"Message to voice channel {channel.name}: {message} by {ctx.author.mention}", file=discord.File(file, attachment.filename))
                        else:
                            await text_channel.send(f"Failed to download attachment from {attachment.url}")
            except Exception as e:
                await ctx.send(f"An error occurred while downloading the attachment: {e}")
        else:
            await text_channel.send(f"Message to voice channel {channel.name}: {message} by {ctx.author.mention}")

# Function to calculate days left
def get_days_left(exam_date):
    today = datetime.now(pytz.timezone("Asia/Kolkata")).replace(hour=0, minute=0, second=0, microsecond=0)
    diff_time = (exam_date - today).days
    return max(diff_time, 0)

# Function to update multiple VC names
async def update_channel_names():
    try:
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            print("Guild not found or bot lacks access")
            return

        for channel_id, channel_info in CHANNELS.items():
            exam = channel_info["exam"]
            exam_date = datetime.fromisoformat(channel_info["date"])

            print(f"Fetching channel: {channel_id}")
            channel = guild.get_channel(int(channel_id))  # Convert channel_id back to integer

            if not channel:
                print(f"Channel {channel_id} not found or bot lacks access")
                continue

            days_left = get_days_left(exam_date)
            new_name = f"{exam} : {days_left} Days"

            if channel.name != new_name:
                await channel.edit(name=new_name)
                print(f"Updated VC name for {exam} to: {new_name}")
            else:
                print(f"No change needed for {exam}")

    except Exception as e:
        print(f"Error updating channel names: {e}")

# Function to calculate the next midnight
def get_next_midnight():
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return midnight

# Run the update function at midnight daily
@tasks.loop(hours=24)
async def scheduled_update():
    print("Updating voice channel names...")
    await update_channel_names()

@scheduled_update.before_loop
async def before_scheduled_update():
    await bot.wait_until_ready()
    print("Bot is ready. Starting scheduled updates...")

    # Calculate the delay until the next midnight
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    midnight = get_next_midnight()
    delay = (midnight - now).total_seconds()

    # Wait until midnight
    print(f"Waiting {delay} seconds until midnight...")
    await asyncio.sleep(delay)

# Slash command to set exam date for a channel
@bot.tree.command(name="setexam", description="Set an exam date for a voice channel")
@app_commands.describe(
    channel_id="The ID of the voice channel",
    exam_name="The name of the exam",
    exam_date="The exam date (YYYY-MM-DD)"
)
async def set_exam(interaction: discord.Interaction, channel_id: str, exam_name: str, exam_date: str):
    try:
        # Parse the date string into a datetime object
        exam_date = datetime.strptime(exam_date, "%Y-%m-%d").replace(tzinfo=pytz.timezone("Asia/Kolkata"))

        # Add or update the channel in the CHANNELS dictionary
        CHANNELS[channel_id] = {"exam": exam_name, "date": exam_date.isoformat()}

        # Save the updated data to the file
        save_data(CHANNELS)

        # Confirm to the user
        await interaction.response.send_message(
            f"Exam date set for channel {channel_id}: {exam_name} on {exam_date.strftime('%Y-%m-%d')}"
        )

        # Update the channel name immediately
        await update_channel_names()

    except ValueError:
        await interaction.response.send_message("Invalid date format. Please use `YYYY-MM-DD`.", ephemeral=True)

# Slash command to remove an exam date for a channel
@bot.tree.command(name="removeexam", description="Remove an exam date for a voice channel")
@app_commands.describe(
    channel_id="The ID of the voice channel"
)
async def remove_exam(interaction: discord.Interaction, channel_id: str):
    if channel_id in CHANNELS:
        # Remove the channel from the CHANNELS dictionary
        del CHANNELS[channel_id]

        # Save the updated data to the file
        save_data(CHANNELS)

        # Confirm to the user
        await interaction.response.send_message(
            f"Exam date removed for channel {channel_id}."
        )

        # Update the channel name immediately
        await update_channel_names()
    else:
        await interaction.response.send_message(
            f"No exam date found for channel {channel_id}.", ephemeral=True
        )

# Ticket System Code (make sure you are entering in this section now which has no connection with moderation commands.)
async def setup_ticket_creation_message():
    """Setup the ticket creation message with a dropdown menu."""
    global TICKET_CREATION_MESSAGE_ID

    channel = bot.get_channel(TICKET_CREATION_CHANNEL_ID)
    if not channel:
        print("Ticket creation channel not found!")
        return

    # Check if the message already exists
    if TICKET_CREATION_MESSAGE_ID:
        try:
            message = await channel.fetch_message(TICKET_CREATION_MESSAGE_ID)
            print("Ticket creation message already exists. Reattaching the view...")

            # Reattach the view to the existing message
            select = Select(
                placeholder="Select your issue",
                options=[
                    discord.SelectOption(label="Help Desk", value="help_desk", emoji="🛠️"),
                    discord.SelectOption(label="Apply for Staff", value="apply_for_staff", emoji="📝"),
                    discord.SelectOption(label="Request of Ban", value="request_of_ban", emoji="🔒"),
                ],
            )

            async def select_callback(interaction):
                if select.values[0] == "apply_for_staff":
                    await interaction.response.send_modal(StaffApplicationModal())
                else:
                    await create_ticket(interaction, select.values[0])

            select.callback = select_callback

            view = View(timeout=None)  # Persistent view
            view.add_item(select)

            await message.edit(view=view)
            return
        except discord.NotFound:
            print("Ticket creation message not found. Creating a new one.")

    # Create the dropdown menu
    select = Select(
        placeholder="Select your issue",
        options=[
            discord.SelectOption(label="Help Desk", value="help_desk", emoji="🛠️"),
            discord.SelectOption(label="Apply for Staff", value="apply_for_staff", emoji="📝"),
            discord.SelectOption(label="Request of Ban", value="request_of_ban", emoji="🔒"),
        ],
    )

    async def select_callback(interaction):
        if select.values[0] == "apply_for_staff":
            await interaction.response.send_modal(StaffApplicationModal())
        else:
            await create_ticket(interaction, select.values[0])

    select.callback = select_callback

    # Create the view (persistent)
    view = View(timeout=None)  # No timeout to keep the view active
    view.add_item(select)

    # Send the message
    message = await channel.send(
        "**Open a ticket!**\nPlease select the option from the dropdown menu as per your issue.",
        view=view,
    )
    TICKET_CREATION_MESSAGE_ID = message.id
    save_ticket_creation_message_id()

# Modal for staff application
class StaffApplicationModal(Modal, title="Staff Application"):
    """Modal for staff application questions."""
    role = TextInput(label="Applying for which role?", placeholder="e.g., Moderator", required=True)
    studying = TextInput(label="What are you currently studying for?", placeholder="e.g., Computer Science", required=True)
    timings = TextInput(label="Active timings?", placeholder="e.g., 6 PM - 10 PM", required=True)
    cam_preference = TextInput(label="Prefer cam/non-cam sessions?", placeholder="e.g., Cam", required=True)
    experience = TextInput(label="Past experiences in moderation?", placeholder="e.g., 2 years as a Discord mod", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, "apply_for_staff", self)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        # Reset the dropdown if the user cancels the modal
        await reset_dropdown(interaction)
        await interaction.response.send_message("Modal cancelled. Please try again.", ephemeral=True)

# Create a ticket channel
async def create_ticket(interaction, issue_type, modal=None):
    """Create a ticket channel."""
    global ticket_counter

    try:
        # Acknowledge the interaction immediately
        await interaction.response.defer(ephemeral=True)

        # Increment the ticket counter
        ticket_counter += 1
        save_ticket_counter()

        # Create the ticket channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(SUPPORT_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        category = discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"ticket-{ticket_counter}",
            overwrites=overwrites,
            category=category,
        )

        # Store the ticket details with the ticket_id as a string
        ticket_id_str = str(ticket_counter)  # Convert ticket_id to a string
        tickets[ticket_id_str] = {
            "channel_id": ticket_channel.id,
            "opened_by": interaction.user.id,
            "opened_time": datetime.now().isoformat(),
            "claimed_by": None,
            "closed_by": None,
            "closed_time": None,
            "reason": None,
            "issue_type": issue_type,
        }
        save_tickets()  # Save ticket data
        # Send a welcome message in the ticket channel
        embed = discord.Embed(
            title=f"Ticket #{ticket_id_str}",
            description=f"Hello {interaction.user.mention}, a support representative will be with you shortly.\n\n**Issue Type:** {issue_type.replace('_', ' ').title()}",
            color=discord.Color.green(),
        )
        await ticket_channel.send(embed=embed)

        # If it's a staff application, send the answers
        if issue_type == "apply_for_staff" and modal:
            embed = discord.Embed(
                title="Staff Application Answers",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Applying for which role?", value=modal.role.value, inline=False)
            embed.add_field(name="What are you currently studying for?", value=modal.studying.value, inline=False)
            embed.add_field(name="Active timings?", value=modal.timings.value, inline=False)
            embed.add_field(name="Prefer cam/non-cam sessions?", value=modal.cam_preference.value, inline=False)
            embed.add_field(name="Past experiences in moderation?", value=modal.experience.value, inline=False)
            await ticket_channel.send(embed=embed)

        # Ping the appropriate role based on the issue type
        if issue_type == "help_desk":
            role = interaction.guild.get_role(MOD_ROLE_ID)
        elif issue_type == "request_of_ban":
            role = interaction.guild.get_role(ELDER_ROLE_ID)
        elif issue_type == "apply_for_staff":
            role = interaction.guild.get_role(ADMIN_ROLE_ID)
        else:
            role = None

        if role:
            await ticket_channel.send(f"{role.mention}")

        # Add buttons for claiming and closing the ticket
        claim_button = Button(label="Claim Ticket", style=discord.ButtonStyle.primary, emoji="🛠️", custom_id=f"claim_{ticket_id_str}")
        close_button = Button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id=f"close_{ticket_id_str}")

        async def claim_button_callback(interaction):
            # Check if the user has the staff role
            staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
            if staff_role not in interaction.user.roles:
                await interaction.response.send_message("You do not have permission to claim tickets!", ephemeral=True)
                return

            tickets[ticket_id_str]["claimed_by"] = interaction.user.id
            save_tickets()  # Save ticket data
            await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}.")

        async def close_button_callback(interaction):
            # Open the modal to ask for the reason
            modal = CloseTicketModal()
            modal.custom_id = f"close_ticket_{ticket_id_str}"  # Pass the ticket ID to the modal
            await interaction.response.send_modal(modal)

        claim_button.callback = claim_button_callback
        close_button.callback = close_button_callback

        view = View(timeout=None)
        view.add_item(claim_button)
        view.add_item(close_button)

        await ticket_channel.send("Please select an action:", view=view)

        # Send a follow-up message to the user
        await interaction.followup.send(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

        # Reset the dropdown
        await reset_dropdown(interaction)
    except Exception as e:
        print(f"Error creating ticket: {e}")
        await interaction.followup.send("An error occurred while creating the ticket.", ephemeral=True)

# Close a ticket
async def close_ticket(interaction, ticket_id, reason):
    """Close the ticket."""
    # Convert ticket_id to a string to match the keys in the tickets dictionary
    ticket_id_str = str(ticket_id)

    ticket = tickets.get(ticket_id_str)  # Access the ticket using the string key
    if not ticket:
        await interaction.response.send_message("Ticket not found!", ephemeral=True)
        # Remove the ticket from the tickets dictionary if it doesn't exist
        tickets.pop(ticket_id_str, None)
        save_tickets()
        return

    # Check if the user has the staff role
    staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to close tickets!", ephemeral=True)
        return

    # Acknowledge the interaction immediately
    await interaction.response.defer(ephemeral=True)

    # Fetch the channel directly from the API
    try:
        ticket_channel = await interaction.guild.fetch_channel(ticket["channel_id"])
        print(f"Found ticket channel: {ticket_channel.name} (ID: {ticket_channel.id})")
    except discord.NotFound:
        await interaction.followup.send("Ticket channel not found!", ephemeral=True)
        # Remove the ticket from the tickets dictionary since the channel no longer exists
        tickets.pop(ticket_id_str)
        save_tickets()
        return
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to access the ticket channel!", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.followup.send(f"An error occurred while fetching the channel: {e}", ephemeral=True)
        return

    # Update ticket details
    ticket["closed_by"] = interaction.user.id
    ticket["closed_time"] = datetime.now().isoformat()
    ticket["reason"] = reason
    save_tickets()

    try:
        # Capture the transcript
        transcript_html = await capture_transcript(ticket_channel)
        transcript_url = await upload_to_github(transcript_html, ticket_id_str)

        # Send the response to the interaction
        await interaction.followup.send("Ticket closed.", ephemeral=True)

        # Log the ticket closure and send transcript link to transcripts channel
        if transcript_url:
            await log_ticket(ticket_id_str, interaction.user, "Closed", reason, transcript_url)

        # Delete the ticket channel
        await ticket_channel.delete()
    except Exception as e:
        print(f"Error closing ticket: {e}")
        await interaction.followup.send("An error occurred while closing the ticket.", ephemeral=True)

# Modal for closing a ticket
class CloseTicketModal(Modal, title="Close Ticket"):
    """Modal to ask for the reason when closing a ticket."""
    reason = TextInput(label="Reason for closing the ticket", placeholder="Enter the reason...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        # Get the ticket ID from the custom_id of the button
        ticket_id = interaction.data["custom_id"].split("_")[-1]  # Extract ticket_id as a string
        print(f"Modal submitted for ticket {ticket_id} (type: {type(ticket_id)})")
        await close_ticket(interaction, ticket_id, self.reason.value)

async def capture_transcript(channel):
    """Capture all messages in the channel and format them into an HTML transcript."""
    messages = []
    users = {}  # Dictionary to store user IDs and usernames

    async for message in channel.history(limit=None, oldest_first=True):
        # Store user information
        users[str(message.author.id)] = message.author.name

        # Prepare message data
        message_data = {
            "author": message.author.name,
            "author_id": message.author.id,
            "author_avatar": message.author.avatar.url if message.author.avatar else "https://cdn.discordapp.com/embed/avatars/0.png",
            "author_role_color": "#FFFFFF",  # Default color (you can fetch the user's role color if needed)
            "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "content": message.content,
            "embeds": [embed.to_dict() for embed in message.embeds],
        }
        messages.append(message_data)

    # Render the HTML template
    template = env.from_string(html_template)
    transcript_html = template.render(messages=messages, users=users)
    return transcript_html

# Upload transcript to GitHub
async def upload_to_github(html_content, ticket_id):
    """Upload the HTML transcript to a GitHub repository."""
    repo_owner = "Pradyumna2669"  # Your GitHub username
    repo_name = "discord-ticket-transcripts"  # Your repository name
    branch = "main"
    file_path = f"transcripts/ticket_{ticket_id}.html"

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        # Check if the file already exists
        response = requests.get(url, headers=headers)
        sha = None
        if response.status_code == 200:
            sha = response.json().get("sha")

        data = {
            "message": f"Add transcript for ticket {ticket_id}",
            "content": base64.b64encode(html_content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if sha:
            data["sha"] = sha  # Include the sha if the file exists

        response = requests.put(url, json=data, headers=headers)
        if response.status_code == 201 or response.status_code == 200:
            # Return the custom GitHub Pages URL
            return f"https://{repo_owner}.github.io/{repo_name}/{file_path}"
        else:
            print(f"Failed to upload transcript: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error uploading transcript: {e}")
        return None

# Log ticket details in the transcripts channel
async def log_ticket(ticket_id, user, action, reason=None, transcript_url=None):
    """Log ticket details in the transcripts channel."""
    ticket = tickets.get(ticket_id)
    if not ticket:
        return

    # Format the log message
    embed = discord.Embed(
        title=f"Ticket #{ticket_id} {action}",
        color=discord.Color.blue(),
    )
    embed.add_field(name=":id: Ticket ID", value=ticket_id, inline=False)
    embed.add_field(name=":open: Opened By", value=f"<@{ticket['opened_by']}>", inline=False)
    embed.add_field(name=":close: Closed By", value=f"<@{ticket['closed_by']}>" if ticket["closed_by"] else "Not closed", inline=False)
    embed.add_field(name=":opentime: Open Time", value=ticket["opened_time"], inline=False)
    embed.add_field(name=":claim: Claimed By", value=f"<@{ticket['claimed_by']}>" if ticket["claimed_by"] else "Not claimed", inline=False)
    embed.add_field(name=":reason: Reason", value=reason or "No reason provided", inline=False)
    embed.add_field(name=":question: Issue Type", value=ticket["issue_type"].replace("_", " ").title(), inline=False)

    if transcript_url:
        embed.add_field(name=":link: Transcript", value=f"[View Transcript]({transcript_url})", inline=False)

    # Send the log message to the transcripts channel
    log_channel = bot.get_channel(TRANSCRIPTS_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=embed)

# Reattach views to existing tickets
async def reattach_ticket_views():
    """Reattach views to existing ticket messages."""
    for ticket_id, ticket in tickets.items():
        channel = bot.get_channel(ticket["channel_id"])
        if channel:
            # Reattach the claim and close buttons
            claim_button = Button(label="Claim Ticket", style=discord.ButtonStyle.primary, emoji="🛠️", custom_id=f"claim_{ticket_id}")
            close_button = Button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id=f"close_{ticket_id}")

            async def claim_button_callback(interaction):
                # Check if the user has the staff role
                staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
                if staff_role not in interaction.user.roles:
                    await interaction.response.send_message("You do not have permission to claim tickets!", ephemeral=True)
                    return

                tickets[ticket_id]["claimed_by"] = interaction.user.id
                await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}.")

            async def close_button_callback(interaction):
    # Extract the ticket ID from the custom_id of the button
                ticket_id = int(interaction.data["custom_id"].split("_")[-1])  # Ensure ticket_id is an integer
                print(f"Closing ticket {ticket_id} (type: {type(ticket_id)})")  # Debugging: Print ticket ID and type

    # Open the modal to ask for the reason
                modal = CloseTicketModal()
                modal.custom_id = f"close_ticket_{ticket_id}"  # Pass the ticket ID to the modal
                await interaction.response.send_modal(modal)

            claim_button.callback = claim_button_callback
            close_button.callback = close_button_callback

            view = View(timeout=None)
            view.add_item(claim_button)
            view.add_item(close_button)

            # Find the message with the buttons and reattach the view
            async for message in channel.history(limit=100):
                if message.author == bot.user and "Please select an action:" in message.content:
                    await message.edit(view=view)
                    break

async def reset_dropdown(interaction):
    """Reset the dropdown menu."""
    channel = bot.get_channel(TICKET_CREATION_CHANNEL_ID)
    if not channel:
        print("Ticket creation channel not found!")
        return

    # Create the dropdown menu
    select = Select(
        placeholder="Select your issue",
        options=[
            discord.SelectOption(label="Help Desk", value="help_desk", emoji="🛠️"),
            discord.SelectOption(label="Apply for Staff", value="apply_for_staff", emoji="📝"),
            discord.SelectOption(label="Request of Ban", value="request_of_ban", emoji="🔒"),
        ],
    )

    async def select_callback(interaction):
        if select.values[0] == "apply_for_staff":
            await interaction.response.send_modal(StaffApplicationModal())
        else:
            await create_ticket(interaction, select.values[0])

    select.callback = select_callback

    # Create the view (persistent)
    view = View(timeout=None)  # No timeout to keep the view active
    view.add_item(select)

    # Edit the original message to reset the dropdown
    try:
        message = await channel.fetch_message(TICKET_CREATION_MESSAGE_ID)
        await message.edit(view=view)
    except discord.NotFound:
        print("Ticket creation message not found.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    if isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
        # Already handled in the command, no need to log
        return
    # Log other errors
    logger.error(f"Error in command {ctx.command}: {error}")

@bot.command()
@has_allowed_role()
async def sync_category(ctx, category: discord.CategoryChannel):
    """Sync permissions for all channels in a category"""
    try:
        # Sync the category first (this updates all channels to match category permissions)
        await category.edit(sync_permissions=True)
        
        # Get all channels in the category
        channels = category.channels
        
        # Count of synced channels
        synced_count = 0
        
        # Sync each channel individually (in case some didn't sync properly)
        for channel in channels:
            try:
                await channel.edit(sync_permissions=True)
                synced_count += 1
            except discord.Forbidden:
                logger.warning(f"Missing permissions to sync {channel.name}")
            except discord.HTTPException as e:
                logger.error(f"Error syncing {channel.name}: {e}")
        
        # Send confirmation
        await ctx.send(f"✅ Successfully synced permissions for category **{category.name}** and its {synced_count} channels.")
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to sync this category!")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Error syncing category: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in sync_category: {e}")
        await ctx.send("❌ An unexpected error occurred while syncing the category.")

@bot.command()
async def help(ctx):
    """Custom help command to explain bot commands in a user-friendly way."""

    embed = discord.Embed(
        title="Bot Commands Help",
        description="Here are the available commands and their descriptions. Use `!command_name` to run each command.",
        color=discord.Color.blue()  # You can change the color as needed
    )

    embed.add_field(
        name="🔧 **Moderation Commands**",
        value=(
            "`!mute @user [reason]` - Mute a user for disruptive behavior.\n"
            "`!unmute @user` - Unmute a previously muted user.\n"
            "`!warn @user [reason]` - Issue a warning to a user.\n"
            "`!warnings @user` - Check how many warnings a user has.\n"
            "`!del_warn @user [count]` - Delete a specific number of warnings for a user.\n"
            "`!kick @user [reason]` - Kick a user from the server.\n"
            "`!ban @user [reason]` - Ban a user from the server."
            "`!send_dm @user [message]` - Send message to any user through bot."
            "`send_invwarn @user` - Send warning for sharing 3rd party server invite."
        ),
        inline=False
    )

    embed.add_field(
        name="📜 **Role Management Commands**",
        value=(
            "`!select_grind` - Select your grind role (Morning, Afternoon, Evening).\n"
            "`!apply` - Apply for the Moderator role (Admins only).\n"
            "`!promote @user` - Promote a Moderator to Elder (Admins only).\n"
            "`!view_applications` - View pending Moderator applications (Admins only).\n"
            "`!approve @user` - Approve a Moderator application (Admins only).\n"
            "`!deny @user` - Deny a Moderator application (Admins only)."
        ),
        inline=False
    )

    embed.add_field(
        name="📚 **Information and Study Commands**",
        value=(
            "`!rule` - View the study room rules.\n"
            "`!apologize` - Send an apology message from the bot.\n"
            "`!help` - Show this help message with all available commands.\n"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ **Miscellaneous**",
        value=(
            "`!ping` - Check if the bot is online and responding.\n"
            "`!serverinfo` - Get information about the current server.\n"
            "`!userinfo @user` - Get information about a specific user."
        ),
        inline=False
    )

    # Send the embed to the channel where the command was used
    await ctx.send(embed=embed)       
                    
bot.run(TOKEN)
