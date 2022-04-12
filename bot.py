#!/usr/bin/env python3

from __future__ import print_function

import asyncio

import os
import datetime
import discord
import logging

from tabulate import tabulate

from pprint import pprint

from dotenv import load_dotenv

from discord.ext import commands
from discord.ext import tasks

from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from apiclient import discovery

from discord_webhook import DiscordWebhook,DiscordEmbed

import httplib2

def parse_world(world):
    worlds = {
            "L": "Lich",
            "O": "Odin",
            "P": "Phoenix",
            "S": "Shiva",
            "T": "Twintania",
            "Z": "Zodiark"
            }

    initial=world[0].capitalize()
    return worlds[initial]

def worldTimeLoc(world,leg=None):
    locs = {
            "Lich": "C3",
            "Odin": "C4",
            "Phoenix": "C5",
            "Shiva": "C6",
            "Twintania": "C7",
            "Zodiark": "C8"
            }
    if leg==1:
        locs = {
                "Lich": "C18",
                "Odin": "C19",
                "Phoenix": "C20",
                "Shiva": "C21",
                "Twintania": "C22",
                "Zodiark": "C23"
                }
    return locs[world]

def worldStatusLoc(world,leg=None):
    locs = {
            "Lich": "E3",
            "Odin": "E4",
            "Phoenix": "E5",
            "Shiva": "E6",
            "Twintania": "E7",
            "Zodiark": "E8"
            }
    if leg==1:
        locs = {
                "Lich": "E18",
                "Odin": "E19",
                "Phoenix": "E20",
                "Shiva": "E21",
                "Twintania": "E22",
                "Zodiark": "E23"
                }
    return locs[world]

async def bot_log(msg):
    await bot.get_channel(LOG_CHANNEL).send(msg)

async def update_channel(server, status, started, legacy=None):

    ids = {
            "Lich": 888868356659228682,
            "Odin": 888868371423191051,
            "Phoenix": 888868382877831188,
            "Shiva": 888868394772860988,
            "Twintania": 888868418361630811,
            "Zodiark": 888868429950484491
            }

    ids_l = {
            "Lich": 895686404531707964,
            "Odin": 895686423351533609,
            "Phoenix": 895686443064766545,
            "Shiva": 895686465483309116,
            "Twintania": 895686484659679343,
            "Zodiark": 895686518335737936
            }
    
    servers = {
            "Lich": "lich",
            "Odin": "odin",
            "Phoenix": "phoe",
            "Shiva": "shiva",
            "Twintania": "twin",
            "Zodiark": "zodi"
            }

    statuses = {
            "Up": "up",
            "Scouting": "scouting",
            "Scouted": "scouted",
            "Running": "run",
            "Dead": "dead",
            "Sniped": "sniped"
            }

    statusicons = {
            "Up": "✅",
            "Scouting": "📡",
            "Scouted": "🌐",
            "Running": "🚋",
            "Dead": "🔒",
            "Sniped": "🏹"
            }
    if legacy != 1:
        chan=bot.get_channel(ids[server])
    else:
        chan=bot.get_channel(ids_l[server])
    newname=f"{statusicons[status]}{servers[server]}-{statuses[status]}"
    if chan.name != newname:
        print("need to update name")
        await chan.edit(name=newname)
    else:
        print("no need to update name")


async def update_sheet(world, status, time, legacy=None):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    creds = None

    secret=os.path.join(os.getcwd(),'nuny.json')
    creds = service_account.Credentials.from_service_account_file(secret,scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)

    sheet=service.spreadsheets()
    timecell="Up Times!"+worldTimeLoc(world,legacy)
    statuscell="Up Times!"+worldStatusLoc(world,legacy)
    if time != 0:
        temp=datetime.datetime(1899,12,30)
        delta=time-temp
        time=float(delta.days)+(float(delta.seconds)/86440)
        body={
                "valueInputOption": "RAW",
                "data": [
                    {
                        'range': timecell,
                        'values': [[time]]
                    },
                    {
                        'range': statuscell,
                        'values': [[status]]
                    }
                ]
            }

    else:
        body={
                "valueInputOption": "RAW",
                "data": [
                    {
                        'range': statuscell,
                        'values': [[status]]
                    }
                ]
            }

    response=sheet.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()

def fetch_sheet(range):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    secret=os.path.join(os.getcwd(),'nuny.json')
    creds = service_account.Credentials.from_service_account_file(secret,scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet=service.spreadsheets()
    try:
        result=sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range, valueRenderOption="UNFORMATTED_VALUE").execute()
    except HttpError as err:
        print(f"HttpError! {err.resp.status}")
        return 0
    return result.get('values', [])


async def update_from_sheets():
    EW_RANGE = 'Up Times!B3:E8'
    LEGACY_RANGE = 'Up Times!B18:E23'

    values=fetch_sheet(EW_RANGE)

    if not values:
        print('No data found.')
    else:
        for row in values:
            if ready == 1:
                await update_channel(row[0],row[3],datetime.datetime(1899,12,30)+datetime.timedelta(days=row[1]),0)

    values=fetch_sheet(LEGACY_RANGE)

    if not values:
        print('No data found.')
    else:
        for row in values:
            if ready == 1:
                await update_channel(row[0],row[3],datetime.datetime(1899,12,30)+datetime.timedelta(days=row[1]),1)



async def update_from_sheets_to_chat(legacy=None):
    range = 'Up Times!B3:E8'
    message="Endwalker status\n```"
    if legacy==1:
        range = 'Up Times!B18:E23'
        message="Shadowbringers status\n```"
    
    values=fetch_sheet(range)

    if not values:
        print('No data found.')
    else:
        taulu=[]
        taulu.append(["Server","Status\nchanged","+6h","Status\nduration","Status"])
        for row in values:
            if ready == 1:
                t1=datetime.datetime.strftime(datetime.datetime(1899,12,30)+datetime.timedelta(days=row[1]),"%d.%m %H:%M")
                if row[3]=="Dead":
                    t2=datetime.datetime.strftime(datetime.datetime(1899,12,30)+datetime.timedelta(days=row[2]),"%H:%M")
                else:
                    t2=""
                t3_td=datetime.datetime.utcnow()-(datetime.datetime(1899,12,30)+datetime.timedelta(days=row[1]))
                t3_h=int(divmod(t3_td.total_seconds(),3600)[0])
                t3_m=int(divmod(divmod(t3_td.total_seconds(),3600)[1],60)[0])
                t3=f"{t3_h}:{t3_m:02d}"
                
                taulu.append([row[0],t1,t2,t3,row[3]])
    message+=tabulate(taulu,headers="firstrow",tablefmt="fancy_grid")+"```"
    return message

def delta_to_words(delta):
    delta=abs(delta)
    delta_d=int(divmod(delta.total_seconds(),86400)[0])
    delta_h=int(divmod(divmod(delta.total_seconds(),86400)[1],3600)[0])
    delta_m=int(divmod(divmod(delta.total_seconds(),3600)[1],60)[0])
    
    msg=""
    if delta_d>0:
        msg=f"{delta_d} days, "
    if delta_h>0:
        msg+=f"{delta_h} hours and "
    msg+=f"{delta_m} minutes"
    return msg

def spec_delta(time,start_s,end_s,type):
    now=datetime.datetime.utcnow()
    start=time+datetime.timedelta(seconds=start_s)-now
    end=time+datetime.timedelta(seconds=end_s)-now
    st=delta_to_words(start)
    en=delta_to_words(end)
    if type=="spawn":
        if int(start.total_seconds())>0:
            msg=f"Marks have been despawned and will start spawning in {st} and will be fully spawned in {en}."
        else:
            msg=f"Marks have started spawning {st} ago and should be fully spawned in {en}."
    else:
        if int(start.total_seconds())>0:
            msg=f"Marks are up and will start despawning in {st} and will be fully despawned in {en}."
        else:
            msg=f"Marks have started to despawn {st} ago and will be fully despawned in {en}."
    return msg


def speculate(world,legacy=None):
    now=datetime.datetime.utcnow()
    l=0
    if legacy[0].capitalize()=="L":
        l=1
    w=parse_world(world)

    timecell="Up Times!"+worldTimeLoc(w,l)
    statuscell="Up Times!"+worldStatusLoc(w,l)

    time=datetime.datetime(1899,12,30)+datetime.timedelta(days=fetch_sheet(timecell)[0][0])
    delta=now-time
    status=fetch_sheet(statuscell)[0][0]

    msg=f"Status **{status}** for **{w}** was set at {time}.\n"
    if status=="Dead":
        msg+=spec_delta(time,12600,21600,"spawn")
    if status=="Up":
        dur=now-time+datetime.timedelta(hours=0)
        if int(dur.total_seconds())<86400:
            msg+=spec_delta(time,77400,86400,"despawn")
        else:
            if int(dur.total_seconds())<108000:
                msg+=spec_delta(time,91800,108000,"spawn")
            else:
                if int(dur.total_seconds())<194400:
                    msg+=spec_delta(time,178200,194400,"despawn")
                else:
                    if int(dur.total_seconds())<216000:
                        msg+=spec_delta(time,192600,216000,"spawn")
                    else:
                        if int(dur.total_seconds())<302400:
                            msg+=spec_delta(time,279000,302400,"despawn")
                        else:
                            if int(dur.total_seconds())<324000:
                                msg+=spec_delta(time,293400,324000,"spawn")
                            else:
                                msg+="Condition uncertain, try to run trains more often."
    return msg
 
def parse_parameters(time,leg):
    try:
        if time==None:
            time=datetime.datetime.utcnow()
        else:
            if time[0].capitalize()=="L":
                leg="L"
                time=datetime.datetime.utcnow()
            else:
                if time[0]=="+":
                    time=datetime.timedelta(minutes=int(time[1:]))+datetime.datetime.utcnow()
                else:
                    t=time.split(":")
                    h=int(t[0])
                    m=int(t[1])
                    time=datetime.datetime.utcnow().replace(hour=h,minute=m,second=45)
    except ValueError:
        time=datetime.datetime.utcnow()
    l=0
    if leg[0].capitalize()=="L":
        l=1
    return [time,l]

def webhook_shout(webhook,role,embed):
    mentions={
            "roles": [role]
            }
    if role==0:
        msg="Hunt train is about to start!"
    else:
        msg=f"<@&{role}> train is about to start!"
    webhook = DiscordWebhook(url=webhook,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
    webhook.add_embed(embed)
    resp=webhook.execute()

logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN=os.getenv('DISCORD_TOKEN')
SPREADSHEET_ID=os.getenv('SPREADSHEET_ID')
LOG_CHANNEL=int(os.getenv('LOG_CHANNEL'))
BOT_CHANNEL=int(os.getenv('BOT_CHANNEL'))
WEBHOOK_TEST=os.getenv('WEBHOOK_TEST')
WEBHOOK_ESC=os.getenv('WEBHOOK_ESC_FC')
WEBHOOK_CC=os.getenv('WEBHOOK_CC')
WEBHOOK_CH=os.getenv('WEBHOOK_CH')
WEBHOOK_ANGEL=os.getenv('WEBHOOK_ANGEL')
WEBHOOK_FALOOP=os.getenv('WEBHOOK_FALOOP')
WEBHOOK_WRKJN=os.getenv('WEBHOOK_WRKJN')
WEBHOOK_KETTU=os.getenv('WEBHOOK_KETTU')
WEBHOOK_HAO=os.getenv('WEBHOOK_HAO')
ROLE_EW_TEST=int(os.getenv('ROLE_TEST_EW'))
ROLE_SHB_TEST=int(os.getenv('ROLE_TEST_SHB'))
ROLE_EW_ESC=int(os.getenv('ROLE_ESC_FC'))
ROLE_SHB_ESC=int(os.getenv('ROLE_ESC_FC'))
ROLE_EW_CC=int(os.getenv('ROLE_CC_EW'))
ROLE_SHB_CC=int(os.getenv('ROLE_CC_SHB'))
ROLE_EW_CH=int(os.getenv('ROLE_CH_EW'))
ROLE_SHB_CH=int(os.getenv('ROLE_CH_SHB'))
ROLE_EW_FALOOP=int(os.getenv('ROLE_FALOOP_EW'))
ROLE_SHB_FALOOP=int(os.getenv('ROLE_FALOOP_SHB'))
ROLE_EW_KETTU=int(os.getenv('ROLE_KETTU_EW'))
ROLE_SHB_KETTU=int(os.getenv('ROLE_KETTU_SHB'))
ROLE_HAO=int(os.getenv('ROLE_HAO'))

ready = 0

bot = commands.Bot(command_prefix=".")

@bot.command(name='speculate',help='Speculate about status of a certain world')
async def spec(ctx,world,legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    msg=speculate(world,legacy)
    await ctx.send(msg)

@bot.command(name='scout', aliases=['sc','scouting'],help='Begin scouting.\nTime parameter is optional and can be in form "+15" (minutes) or "15:24" (server time)')
async def scouting(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    world=parse_world(world)
    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]
    await update_sheet(world,"Scouting",time,l)
    await update_channel(world,"Scouting",time,l)
    await ctx.message.add_reaction("✅")


@bot.command(name='scouted', aliases=['scdone','scend'],help='End scouting.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def scoutend(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    world=parse_world(world)
    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]

    await update_sheet(world,"Scouted",time,l)
    await ctx.message.add_reaction("✅")


@bot.command(name='start', aliases=['begin','run','go'],help='Start train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def begintrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    world=parse_world(world)
    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]

    await update_sheet(world,"Running",time,l)
    await ctx.message.add_reaction("✅")


@bot.command(name='end', aliases=['done','dead','finish'],help='Finish train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def endtrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    world=parse_world(world)
    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]

    await update_sheet(world,"Dead",time,l)
    await ctx.message.add_reaction("✅")


@bot.command(name='up', aliases=['reset'],help='Reset train')
async def resettrain(ctx, world, time=None,legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    world=parse_world(world)
    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]

    await update_sheet(world,"Up",time,l)
    await ctx.message.add_reaction("✅")


@bot.command(name="status", aliases=['getstatus','stat'],help='Get train status')
async def getstatus(ctx, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    leg=0
    if legacy[0].capitalize() == "L":
        leg=1
    msg=await update_from_sheets_to_chat(leg)
    await ctx.send(msg)
    await ctx.message.add_reaction("✅")

@bot.command(name="testadvertise", aliases=['testshout','testsh'],help='Advertise your train. Put multi-part parameters in quotes (eg. .shout twin "Fort Jobb"). Any attached image wil be included in the shout')
async def advertise(ctx, world, start, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    world=parse_world(world)
    parm=parse_parameters(None,legacy)
    l=parm[1]
    if l==0:
        role="@Endwalker_role"
    else:
        role="@Legacy_role"


    username=ctx.message.author.display_name
    user_avatar=ctx.message.author.avatar_url

    imageurl=""

    if ctx.message.attachments:
        imageurl=str(ctx.message.attachments[0].url)

    embed=discord.Embed(
            title="Hunt train will start in 10 minutes")
    embed.set_author(name=str(username),icon_url=str(user_avatar))
    embed.add_field(name="Server", value=world, inline=True)
    embed.add_field(name="Start location", value=start)
            
    if imageurl!="":
        embed.set_image(url=imageurl)

    msg=f"About to send this notification to the test server (react with ✅ to send or wait 15 sec to cancel):\n\n{role} train is about to start!"

    msg1=await ctx.send(msg,embed=embed)
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await bot.wait_for("reaction_add", check=check,timeout=15)
    except asyncio.TimeoutError:
        print ("Timed out")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user=res
            print (reaction.emoji)

            embed=DiscordEmbed(
                title="Hunt train will start in 10 minutes")
            embed.set_author(name=str(username),icon_url=str(user_avatar))
            embed.add_embed_field(name="Server", value=world, inline=True)
            embed.add_embed_field(name="Start location", value=start)

            if imageurl!="":
                embed.set_image(url=imageurl)

# test server
            print ("test")
            if l==0:
                role=ROLE_EW_TEST
            else:
                role=ROLE_SHB_TEST

            webhook_shout(WEBHOOK_TEST,role,embed)

            await msg1.delete()
            await ctx.message.add_reaction('✅')

@bot.command(name="testadvertise2", aliases=['testshout2','testsh2'],help='Advertise your train. Put multi-part parameters in quotes (eg. .testsh2 "message text here" [image_url] [legacy])')
async def advertise(ctx, message, imageurl="", legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    username=ctx.message.author.display_name
    user_avatar=ctx.message.author.avatar_url

    if imageurl=="l":
        legacy="l"
        imageurl=""

    if ctx.message.attachments:
        imageurl=str(ctx.message.attachments[0].url)

    parm=parse_parameters(None,legacy)
    l=parm[1]
    if l==0:
        roletext="@Endwalker_role"
    else:
        roletext="@Legacy_role"

    msg="About to send this notification to test server:"
    embed=discord.Embed(
            title=f"{roletext} train is about to start!",
            description=message)
    embed.set_author(name=username,icon_url=user_avatar)
    if imageurl!="":
        embed.set_image(url=imageurl)
    try:
        msg1=await ctx.send(msg,embed=embed)
    except:
        await ctx.message.add_reaction('❌')
        await ctx.send("Invalid url or image")
        return

    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await bot.wait_for("reaction_add", check=check,timeout=15)
    except asyncio.TimeoutError:
        print ("Timed out")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user=res
            print (reaction.emoji)

            embed=DiscordEmbed(description=str(message))
            embed.set_author(name=str(username),icon_url=str(user_avatar))
            if imageurl!="":
                embed.set_image(url=str(imageurl))

# test server
            print ("test")
        
            if l==0:
                role=ROLE_EW_TEST
            else:
                role=ROLE_SHB_TEST
            webhook_shout(WEBHOOK_TEST,role,embed)

            await msg1.delete()
            await ctx.message.add_reaction('✅')

@bot.command(name="advertise", aliases=['ad','shout','sh'],help='Advertise your train. Put multi-part parameters in quotes (eg. .shout twin "Fort Jobb"). Additionally will set the server status to running.')
async def advertise(ctx, world, start, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return

    username=ctx.message.author.display_name

    world=parse_world(world)
    parm=parse_parameters(None,legacy)
    l=parm[1]
    if l==0:
        msg=f"About to send this notification to Faloop, CH and CC servers: ```@Endwalker_role **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 15 seconds to cancel."
    if l==1:
        msg=f"About to send this notification to Faloop, CH and CC servers: ```@Legacy_role **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 15 seconds to cancel."

    msg1=await ctx.send(msg)
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await bot.wait_for("reaction_add", check=check,timeout=15)
    except asyncio.TimeoutError:
        print ("Timed out")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user=res
            print (reaction.emoji)

# test server 
            print ("test")
            mentions={
                "roles": [ROLE_EW_TEST, ROLE_SHB_TEST]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_TEST}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_TEST}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_TEST,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

# kettu server
            print ("kettu")
            mentions={
                "roles": [ROLE_EW_KETTU, ROLE_SHB_KETTU]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_KETTU}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_KETTU}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_KETTU,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()


# ch server
            print ("ch")
            mentions={
                "roles": [ROLE_EW_CH, ROLE_SHB_CH]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_CH}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_CH}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_CH,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

# cc server
            print ("cc")
            mentions={
                "roles": [ROLE_EW_CC, ROLE_SHB_CC]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_CC}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_CC}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_CC,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

# esc server
            print ("esc")
            mentions={
                "roles": [ROLE_EW_ESC]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_ESC}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_ESC}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_ESC,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

# angel server
            print ("angel")
            if l==0:
                msg=f"[{world}] Hunt train starting in 10 minutes at {start} (Conductor: {username})."
                webhook = DiscordWebhook(url=WEBHOOK_ANGEL,rate_limit_retry=True,content=msg,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
                resp=webhook.execute()

# wrkjn server
            print ("wrkjn")
            if l==0:
                msg=f"[{world}] Hunt train starting in 10 minutes at {start} (Conductor: {username})."
                webhook = DiscordWebhook(url=WEBHOOK_WRKJN,rate_limit_retry=True,content=msg,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
                resp=webhook.execute()

# hao server
            print ("hao")
            mentions={
                    "roles": [ROLE_HAO]
            }
            msg=f"<@&{ROLE_HAO}> [{world}] Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_HAO,rate_limit_retry=True,content=msg,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()


# faloop server
            print ("faloop")
            mentions={
                "roles": [ROLE_EW_FALOOP, ROLE_SHB_FALOOP]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_FALOOP}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_FALOOP}> **[{world}]** Hunt train starting in 10 minutes at {start} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_FALOOP,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

            time=parm[0]
            
            await update_sheet(world,"Running",time,l)

            await msg1.delete()
            await ctx.message.add_reaction('✅')

@bot.command(name="advmanual", aliases=['adm','mshout','msh'],help='Advertise your train. Put multi-part parameters in quotes (eg. .mshout "[Twintania] Hunt train starting in 10 minutes at Fort Jobb")')
async def madvertise(ctx, message, legacy="0"):
    if ctx.channel.id != BOT_CHANNEL:
        print (f"{BOT_CHANNEL} != {ctx.channel.id}")
        return
    username=ctx.message.author.display_name

    print (message)

    parm=parse_parameters(None,legacy)
    l=parm[1]
    if l==0:
        msg=f"About to send this notification to Faloop, CH and CC servers: ```@Endwalker_role {message} (Conductor: {username}).```React with ✅ to send or wait 15 seconds to cancel."
    if l==1:
        msg=f"About to send this notification to Faloop, CH and CC servers: ```@Legacy_role {message} (Conductor: {username}).```React with ✅ to send or wait 15 seconds to cancel."

    msg1=await ctx.send(msg)
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await bot.wait_for("reaction_add", check=check,timeout=15)
    except asyncio.TimeoutError:
        print ("Timed out")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user=res
            print (reaction.emoji)

            
# test discord
            print ("test")
            mentions={
                "roles": [ROLE_EW_TEST, ROLE_SHB_TEST]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_TEST}> {message} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_TEST}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_TEST,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

# kettu discord
            print ("test")
            mentions={
                "roles": [ROLE_EW_KETTU, ROLE_SHB_KETTU]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_KETTU}> {message} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_KETTU}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_KETTU,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

# ch discord
            print ("ch")
            mentions={
                "roles": [ROLE_EW_CH, ROLE_SHB_CH]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_CH}> {message} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_CH}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_CH,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

# cc discord
            print ("cc")
            mentions={
                "roles": [ROLE_EW_CC, ROLE_SHB_CC]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_CC}> {message} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_CC}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_CC,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()
	

# esc discord
            print ("esc")
            mentions={
                "roles": [ROLE_EW_ESC]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_ESC}> {message} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_ESC}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_ESC,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()

# angel server
            print ("angel")
            if l==0:
                msg=f"{message} (Conductor: {username})."
                webhook = DiscordWebhook(url=WEBHOOK_ANGEL,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
                resp=webhook.execute()

# wrkjn server
            print ("wrkjn")
            if l==0:
                msg=f"{message} (Conductor: {username})."
                webhook = DiscordWebhook(url=WEBHOOK_WRKJN,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
                resp=webhook.execute()

# hao server
            print ("hao")
            mentions={
                    "roles": [ROLE_HAO]
            }
            msg=f"<@&{ROLE_HAO}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_HAO,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()


# cc discord
            print ("faloop")
            mentions={
                "roles": [ROLE_EW_FALOOP, ROLE_SHB_FALOOP]
            }
            if l==0:
                msg=f"<@&{ROLE_EW_FALOOP}> {message} (Conductor: {username})."
            if l==1:
                msg=f"<@&{ROLE_SHB_FALOOP}> {message} (Conductor: {username})."
            webhook = DiscordWebhook(url=WEBHOOK_FALOOP,rate_limit_retry=True,content=msg,allowed_mentions=mentions,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")
            resp=webhook.execute()



            await msg1.delete()
            await ctx.message.add_reaction('✅')



@bot.event
async def on_ready():
    global ready
    print(f'{bot.user} has connected to Discord!')
    ready=1

@tasks.loop(seconds = 60)
async def STLoop():
    now=datetime.datetime.strftime(datetime.datetime.utcnow(),"%H:%M")
    if ready == 1:
        await bot.change_presence(activity=discord.Game(f"Server time: {now}"))

@tasks.loop(seconds = 300)
async def SheetLoop():
    await update_from_sheets()

SheetLoop.start()
STLoop.start()

bot.run(TOKEN)
