# Discord Bot for Study Server
This is a comprehensive Discord bot designed for managing a study-focused server. It includes features for moderation, role management, ticket systems, and more. The bot is built using the discord.py library and integrates with GitHub for storing ticket transcripts.

# Features
**Moderation**

Mute/Unmute Users: Mute or unmute users with optional reasons.

Warn Users: Issue warnings to users and track their warning count.

Delete Warnings: Remove warnings from a user's record.

NSFW Detection: Automatically detect and handle NSFW content in messages.

Abuse Logging: Log abusive behavior in a dedicated channel.

**Role Management**
Pseudo-Mod Approval: Approve users for pseudo-mod roles.

Mod Promotion: Promote pseudo-mods to full moderators.

Grind Roles: Assign roles based on study grind times (Morning, Afternoon, Evening).

# **Ticket System**

Ticket Creation: Users can create tickets for help, staff applications, or ban requests.

Ticket Management: Staff can claim and close tickets with reasons.

Transcripts: Automatically generate and upload ticket transcripts to GitHub.

# **Study Room Management**

Exam Countdown: Set exam dates for voice channels and display the remaining days in the channel name.

Compliance Monitoring: Ensure users in monitored voice channels are using their cameras or screen sharing.

# **Miscellaneous**
Health Check: Monitor server health metrics (CPU, memory, disk usage).

Custom Help Command: Provide a detailed list of available commands.

Apology Command: Send an official apology message from the bot.

# Setup

Prerequisites
Python 3.8 or higher

discord.py library

GitHub token for uploading ticket transcripts

Discord bot token

**Installation**

Clone the repository:

git clone https://github.com/Pradyumna2669/STXBOT.git
cd STXBOT
Install the required dependencies:

pip install -r requirements.txt
Create a .env file in the root directory and add your Discord bot token and GitHub token:

TOKEN=your_discord_bot_token
GITHUB_TOKEN=your_github_token
Run the bot:

python bot.py
Configuration
Environment Variables
TOKEN: Your Discord bot token.

GITHUB_TOKEN: Your GitHub token for uploading ticket transcripts.

# Role IDs
Modify the role IDs in the code to match your server's roles:

MUTE_ROLE_ID

MOD_ROLE_ID

ELDER_ROLE_ID

STAFF_ROLE_ID

ADMIN_ROLE_ID

PSEUDO_MOD_ROLE_ID

MORNING_GRIND_ROLE_ID

AFTERNOON_GRIND_ROLE_ID

EVENING_GRIND_ROLE_ID

# Channel IDs
Modify the channel IDs in the code to match your server's channels:

TICKET_CREATION_CHANNEL_ID

TRANSCRIPTS_CHANNEL_ID

TICKET_CATEGORY_ID

ABUSE_LOG_CHANNEL_ID

MOD_LOG_CHANNEL_ID

# Usage
**Commands**
**Moderation:**

`!mute @user [reason]: Mute a user.`

`!unmute @user: Unmute a user.`

`!warn @user [reason]: Warn a user.`

`!warnings @user: Check a user's warnings.`

`!del_warn @user [count]: Delete warnings from a user.`

**Role Management:**

`!add_pseudo_mod @user: Add a user to the pseudo-mod approval list.`

`!approve_pseudo_mods: Approve all pseudo-mods.`

`!add_mod @user: Add a user to the mod promotion list.`

`!approve_mods: Approve all mods.`

**Ticket System:**

Use the dropdown menu in the ticket creation channel to create a ticket.

Staff can claim and close tickets using buttons in the ticket channel.

**Study Room Management:**

`/setexam channel_id exam_name exam_date: Set an exam date for a voice channel.`

`/removeexam channel_id: Remove an exam date for a voice channel.`

**Miscellaneous:**

`!health: Check server health metrics.`

`!help: Display a list of available commands.`

# Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

# Acknowledgments
discord.py for the Discord API wrapper.

GitHub API for uploading ticket transcripts.

