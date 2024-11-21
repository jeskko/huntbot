#!/usr/bin/env python3

import asyncio

import datetime
import discord
import logging

from discord.ext import tasks

import nuny.config
import nuny.discord_utils
import nuny.state

from nuny.misc_utils import periodicstatus, update_messages, update_channels, groundskeeper, dailycleanup
from nuny.sonar import websocketrunner

import nuny.commands

logging.basicConfig(level=logging.INFO)
logging.getLogger('websockets.client').setLevel(logging.INFO)

@tasks.loop(seconds = 60)
async def STLoop():
    now=datetime.datetime.strftime(datetime.datetime.utcnow(),"%H:%M")
    await nuny.discord_utils.bot.change_presence(activity=discord.Game(f"Server time: {now}"))
    try:
        await groundskeeper()
    except Exception as e:
        logging.error(f'STLoop error: {e}')

@tasks.loop(seconds = 1800)
async def StatusLoop():
    try:
        await periodicstatus()
    except Exception as e:
        logging.error(f'StatusLoop error: {e}')
        pass

@tasks.loop(hours=24)
async def DailyLoop():
    try:
        await dailycleanup()
    except Exception as e:
        logging.error(f'"DailyLoop error: {e}')
        
@tasks.loop(seconds = 300)
async def ChannelLoop():
    try:
        await update_channels()
        await update_messages()
    except Exception as e:
        logging.error(f'SheetLoop error: {e}')
        pass
    

@nuny.discord_utils.bot.event
async def on_ready():
    logging.info(f'{nuny.discord_utils.bot.user} has connected to Discord!')
    await nuny.discord_utils.check_messages()
    ChannelLoop.start()
    STLoop.start()
    StatusLoop.start() 
    if nuny.config.conf["sonar"]["enable"]==True:
        websocketrunner.start()

async def main():
    nuny.sonar.init_sonar()
    async with nuny.discord_utils.bot:
        await nuny.discord_utils.bot.start(nuny.config.conf["discord"]["token"])

if __name__ == "__main__":
    asyncio.run(main())
