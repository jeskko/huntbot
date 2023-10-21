import discord

from discord.ext import commands
from discord.ext import tasks

discord.VoiceClient.warn_nacl=False

intents=discord.Intents.default()
intents.message_content=True

bot = commands.Bot(command_prefix=".",intents=intents)