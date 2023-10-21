import discord

from discord.ext import commands

discord.VoiceClient.warn_nacl=False

intents=discord.Intents.default()
intents.message_content=True

bot = commands.Bot(command_prefix=".",intents=intents)