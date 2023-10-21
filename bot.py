#!/usr/bin/env python3

import asyncio

import datetime
import discord
import logging

from discord.ext import tasks

import nuny.config
import nuny.discord_utils 
from nuny.misc_utils import periodicstatus
from nuny.sheet_utils import update_from_sheets
from nuny.sonar import websocketrunner 

import nuny.commands

logging.basicConfig(level=logging.INFO)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

@tasks.loop(seconds = 60)
async def STLoop():
    now=datetime.datetime.strftime(datetime.datetime.utcnow(),"%H:%M")
    if ready == 1:
        await nuny.discord_utils.bot.change_presence(activity=discord.Game(f"Server time: {now}"))

@tasks.loop(seconds = 1800)
async def StatusLoop():
    if ready == 1:
        try: 
            await periodicstatus()
        except Exception as e:
             logging.error(f'StatusLoop error: {e}')
             pass

@tasks.loop(seconds = 300)
async def SheetLoop():
    await update_from_sheets()

@nuny.discord_utils.bot.event
async def on_ready():
    global ready
    logging.info(f'{nuny.discord_utils.bot.user} has connected to Discord!')
    ready=1
    SheetLoop.start()
    STLoop.start()
    StatusLoop.start()
    if nuny.config.conf["sonar"]["enable"]==True:
        websocketrunner.start()

async def main():         
    async with nuny.discord_utils.bot:
        await nuny.discord_utils.bot.start(nuny.config.conf["discord"]["token"])

asyncio.run(main())
