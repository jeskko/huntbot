import logging
import discord.errors

import nuny.discord_utils

async def bot_log(msg):
    """Send message on bot log channel."""
    
    try:
        await nuny.discord_utils.bot.get_channel(nuny.config.conf["discord"]["channels"]["log"]).send(msg)
    except discord.errors.DiscordServerError as e:
        logging.error("Bot log message sending failed: {e}")
        pass

async def sonar_log(msg):
    """Send message on sonar log channel."""
    
    try: 
        await nuny.discord_utils.bot.get_channel(nuny.config.conf["discord"]["channels"]["sonar"]).send(msg)
    except discord.errors.DiscordServerError as e:
        logging.error("Sonar log message sending failed: {e}")
        pass
    
async def scout_log(msg):
    """Send message on scout channel."""
    
    try:
        await nuny.discord_utils.bot.get_channel(nuny.config.conf["discord"]["channels"]["bot"]).send(msg)
    except discord.errors.DiscordServerError as e:
        logging.error("Command channel message sending failed: {e}")
        pass
    
async def spec_log(msg):
    """Send message on special log channel."""
    
    try:
        await nuny.discord_utils.bot.get_channel(nuny.config.conf["discord"]["channels"]["special"]).send(msg)
    except discord.errors.DiscordServerError as e:
        logging.error("Special log message sending failed: {e}")
        pass