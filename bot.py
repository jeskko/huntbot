#!/usr/bin/env python3

import asyncio

import os
import datetime
from time import mktime
import discord
import logging
import aiohttp

from tabulate import tabulate

from discord.ext import commands
from discord.ext import tasks

from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google.oauth2 import service_account

import json
from websockets.client import connect
import websockets.exceptions
import sqlite3
import yaml

discord.VoiceClient.warn_nacl=False

with open('config.yaml','r') as file:
    conf=yaml.safe_load(file)

def parse_world(world):
    """
    Convert text input to world name useable on various functions. 
    Really simple, uses only the first letter of the input to figure out which world it is. Works on Light DC but on datacenters with overlapping initial letters this would be a problem.
    Raises ValueError in case of invalid world being tried to be parsed.
    """
    
    initial=world[0].lower()
    w=[w for w in conf["worlds"] if w["initial"]==initial]
    try:
        name=w[0]["name"]
    except IndexError:
        raise ValueError("Invalid world")
    return name

def worldTimeLoc(world,leg=None):
    """
    Find the sheet cell location for time value for a certain world.
    leg==1 means SHB, otherwise EW.
    """
    
    if leg==1:
        l=5
    else:
        l=6
    try: 
        w=[w for w in conf["worlds"] if w["name"]==world][0]
    except IndexError:
        raise ValueError("Invalid world")
    return w[l]["time"]

def worldStatusLoc(world,leg=None):
    """
    Find the sheet cell location for status value for a certain world.
    leg==1 means SHB, otherwise EW.    
    """
    
    if leg==1:
        l=5
    else:
        l=6
    try: 
        w=[w for w in conf["worlds"] if w["name"]==world][0]
    except IndexError:
        raise ValueError("Invalid world")
    return w[l]["status"]

async def bot_log(msg):
    """Send message on bot log channel."""
    
    try:
        await bot.get_channel(conf["discord"]["channels"]["log"]).send(msg)
    except discord.errors.DiscordServerError as e:
        logging.error("Bot log message sending failed: {e}")
        pass

async def sonar_log(msg):
    """Send message on sonar log channel."""
    
    try: 
        await bot.get_channel(conf["discord"]["channels"]["sonar"]).send(msg)
    except discord.errors.DiscordServerError as e:
        logging.error("Sonar log message sending failed: {e}")
        pass
    
async def scout_log(msg):
    """Send message on scout channel."""
    
    try:
        await bot.get_channel(conf["discord"]["channels"]["bot"]).send(msg)
    except discord.errors.DiscordServerError as e:
        logging.error("Command channel message sending failed: {e}")
        pass
    
async def spec_log(msg):
    """Send message on special log channel."""
    
    try:
        await bot.get_channel(conf["discord"]["channels"]["special"]).send(msg)
    except discord.errors.DiscordServerError as e:
        logging.error("Special log message sending failed: {e}")
        pass
    
async def update_channel(world, status, legacy=None):
    """Update channel name value. Will check if actual update is necessary to avoid rate limiting."""
    
    if legacy==1:
        l=5
    else:
        l=6
    try:
        w=[w for w in conf["worlds"] if w["name"]==world][0]
    except IndexError:
        raise ValueError("Invalid world")
    try:
        st=[st for st in conf["statuses"] if st["name"]==status][0]
    except IndexError:
        raise ValueError("Invalid world status")
    chanid=w[l]["channel"]
    newname=f'{st["icon"]}{w["short"]}-{st["short"]}'
     
    chan=bot.get_channel(chanid)
    if chan.name != newname:
        logging.debug(f"Updating channel name from {chan.name} to {newname}.")
        await chan.edit(name=newname)
    else:
        logging.debug("no need to update channel name.")

async def update_sheet(world, status, time, legacy=None):
    """Update the backend sheet."""
    
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

    response=sheet.values().batchUpdate(spreadsheetId=conf["google"]["spreadsheet"], body=body).execute()

def fetch_sheet(range):
    """Fetch data from the backend sheet."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    secret=os.path.join(os.getcwd(),'nuny.json')
    creds = service_account.Credentials.from_service_account_file(secret,scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet=service.spreadsheets()
    try:
        result=sheet.values().get(spreadsheetId=conf["google"]["spreadsheet"], range=range, valueRenderOption="UNFORMATTED_VALUE").execute()
    except HttpError as err:
        logging.error(f"HttpError on fetch_sheet {err.resp.status}")
        return 0
    return result.get('values', [])

async def update_from_sheets():
    """Fetch data from backend sheet and update channel names."""
    
    EW_RANGE = 'Up Times!B3:E10'
    LEGACY_RANGE = 'Up Times!B20:E27'

    values=fetch_sheet(EW_RANGE)

    if not values:
        logging.error('No data found from fetch_sheet.')
    else:
        for row in values:
            if ready == 1:
                await update_channel(row[0],row[3],0)

    values=fetch_sheet(LEGACY_RANGE)

    if not values:
        logging.error('No data found from fetch_sheet.')
    else:
        for row in values:
            if ready == 1:
                await update_channel(row[0],row[3],1)

async def update_from_sheets_to_chat(legacy=None):
    """Fetch status from backend sheet and make a status summary."""
    
    range = 'Up Times!B3:E10'
    message="Endwalker status\n```"
    if legacy==1:
        range = 'Up Times!B20:E27'
        message="Shadowbringers status\n```"
    
    values=fetch_sheet(range)

    if not values:
        logging.error('No data found from fetch_sheet.')
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
                if t3_h<0:
                    t3=""
                else:
                    t3=f"{t3_h}:{t3_m:02d}"
                
                taulu.append([row[0],t1,t2,t3,row[3]])
    message+=tabulate(taulu,headers="firstrow",tablefmt="fancy_grid")+"```"
    return message

async def update_from_sheets_to_compact_chat(legacy=None):
    """Fetch status from backend sheet and make a compact status summary suitable for eg. mobile use."""
    
    range = 'Up Times!B33:D40'
    values=fetch_sheet(range)
    
    if not values:
        logging.error('No data found from fetch_sheet.')
    else:
        taulu=[]
        taulu.append(["Server","EW","SHB"])
        for row in values:
            if ready == 1:
                taulu.append([row[0],row[1],row[2]])
    message="```"+tabulate(taulu,headers="firstrow",tablefmt="fancy_grid")+"```"
    return message


def delta_to_words(delta):
    """Format time delta to words."""
    
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
    """Format timedelta and status to words."""
    
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
    """
    Speculate about hunt marks and their spawn/despawn status.
    https://cdn.discordapp.com/attachments/884351171668619265/972159569658789978/unknown.png
    Also checks Sonar data about the selected world.
    """
    
    now=datetime.datetime.utcnow()
    l=0
    l_text=""
    if legacy[0].capitalize()=="L":
        l=1
        l_text=" (legacy) "
    try:
        w=parse_world(world)
    except ValueError:
        return("Invalid world.")

    timecell="Up Times!"+worldTimeLoc(w,l)
    statuscell="Up Times!"+worldStatusLoc(w,l)

    time=datetime.datetime(1899,12,30)+datetime.timedelta(days=fetch_sheet(timecell)[0][0])
    delta=now-time
    status=fetch_sheet(statuscell)[0][0]

    msg=f"Status **{status}** for **{w}**{l_text} was set at {time}.\n"
    if status=="Dead":
        msg+=spec_delta(time,12600,21600,"spawn")
    if status=="Up" or status=="Scouting" or status=="Scouted":
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
    if conf["sonar"]["enable"]==True:
    # marks probably despawned, last 18 hours
        sel_despawn="""
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastfound < datetime('now', '-22 hours') AND lastfound > datetime('now', '-48 hours') AND currenthp!=0
            """        
    # marks alive, last 18 hours
        sel_alive="""
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastfound > datetime('now', '-22 hours') AND currenthp!=0
            """
        # marks that should have respawned but no sighting
        sel_spawned="""
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastkilled > datetime('now','-20 hours') AND lastkilled < datetime('now','-6 hours') AND currenthp=0
                """
        # marks killed during last 6 hours
        sel_spawning="""
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastkilled > datetime('now','-6 hours') AND lastkilled < datetime('now','-4 hours') AND currenthp=0
                """
        # marks killed during last 4 hours
        sel_dead="""
SELECT count(*) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastkilled > datetime('now','-4 hours') AND currenthp=0
            """

        if l==0:
            exp=5
        else:
            exp=4

        cursor.execute(sel_alive,(exp, w))
        alive=cursor.fetchall()[0][0]

        cursor.execute(sel_despawn,(exp, w))
        despawn=cursor.fetchall()[0][0]
        
        cursor.execute(sel_spawned,(exp, w))
        spawned=cursor.fetchall()[0][0]

        cursor.execute(sel_spawning,(exp, w))
        spawning=cursor.fetchall()[0][0]
        
        cursor.execute(sel_dead,(exp, w))
        dead=cursor.fetchall()[0][0]

        msg+=f"\nSonar data suggests that {alive} marks are alive, {spawned} marks should have spawned, {despawn} marks might have already despawned, {spawning} marks have potential to spawn and {dead} marks are dead."
    return msg

def mapping(world,legacy=None):
    """Fetches mapping data estimate from Sonar."""
    if conf["sonar"]["enable"]==True:
        l=0
        l_text=""
        if legacy[0].capitalize()=="L":
            l=1
            l_text=" (legacy) "

        try:
            w=parse_world(world)
        except ValueError:
            return("Invalid world.")    

        if l==0:
            exp=5
        else:
            exp=4
        
        ishort={0: '',
                1: '',
                2: '',
                3: ''}
        
        ilong={0: '',
            1: '  (Instance ONE)',
            2: '  (Instance TWO)',
            3: '  (Instance THREE)'}
        
        sel="""
    SELECT hunts.name, zones.name,hunt.instanceid, 
        round(((41 / zones.scale) * (((hunt.x + zones.offset_x)*zones.scale + 1024) / 2048)+1),1),
        round(((41 / zones.scale) * (((hunt.y + zones.offset_y)*zones.scale + 1024) / 2048)+1),1) from hunt 
    INNER JOIN hunts on hunts.id = hunt.huntid 
    INNER JOIN worlds on worlds.id=hunt.worldid 
    INNER JOIN zones on zones.id=hunt.zoneid 
    WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastseen > datetime('now','-20 hours') AND lastfound > datetime('now','-20 hours') AND currenthp != 0
    ORDER BY hunt.zoneid,hunt.instanceid
            """
        cursor.execute(sel,(exp,w))
        h=cursor.fetchall()
        msg="Sonar data suggests following mapping:\n```\n"
        for l in h:
            msg+=f"({l[0]}) {l[1]}{ishort[l[2]]} ( {l[3]} , {l[4]} ){ilong[l[2]]}\n"
        msg+="```"
    else:
        msg="Sonar is disabled for this bot, unable to do mapping."
    return msg
 
def parse_parameters(time,leg):
    """Tries to sanitize time and legacy parameters given on a bot command."""
    try:
        if time==None:
            time=datetime.datetime.utcnow()
        else:
            if time[0].capitalize()=="L" or time[0]=="5":
                leg="L"
                time=datetime.datetime.utcnow()
            else:
                if time[0]=="4":
                    leg="4"
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
    stb=0
    if leg[0].capitalize()=="L":
        l=1
    if leg[0]=="5":
        l=1
    if leg[0]=="4":
        stb=1
        l=1
    return [time,l,stb]

logging.basicConfig(level=logging.INFO)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

ready = 0

intents=discord.Intents.default()
intents.message_content=True

bot = commands.Bot(command_prefix=".",intents=intents)

@bot.command(name='speculate',help='Speculate about status of a certain world')
async def spec(ctx,world,legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    msg=speculate(world,legacy)
    await ctx.send(msg)

@bot.command(name='mapping', aliases=["map",], help='Check mapping data from Sonar')
async def spec(ctx,world,legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    msg=mapping(world,legacy)
    await ctx.send(msg)


@bot.command(name='scout', aliases=['sc','scouting'],help='Begin scouting.')
async def scouting(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()
    
    parm=parse_parameters(time,legacy)
    time=0
    l=parm[1]
    stb=parm[2]
    if stb==0:
        statuscell="Up Times!"+worldStatusLoc(world,l)
        status=fetch_sheet(statuscell)[0][0]
        if status=="Dead":
            await ctx.send("Scouting a dead world, adjusting timer.")
            timecell="Up Times!"+worldTimeLoc(world,l)
            time=datetime.datetime(1899,12,30)+datetime.timedelta(days=fetch_sheet(timecell)[0][0])+datetime.timedelta(hours=6)    
        await update_sheet(world,"Scouting",time,l)
        await update_channel(world,"Scouting",l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")

@bot.command(name='scoutcancel', aliases=['cancel', 'sccancel', 'scc'], help="Cancel scouting. Return server to up status.")
async def scoutcancel(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(time,legacy)
    l=parm[1]
    stb=parm[2]
    status="Up"
    if stb==0:
        timecell="Up Times!"+worldTimeLoc(world,l)
        time=datetime.datetime(1899,12,30)+datetime.timedelta(days=fetch_sheet(timecell)[0][0])
        if time>datetime.datetime.utcnow():
            time=time-datetime.timedelta(hours=6)
            status="Dead"
            await ctx.send("Adjusting time -6h and status to dead because timestamp in future.")
        else:
            time=0
        await update_sheet(world,status,time,l)
        await update_channel(world,status,l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")

@bot.command(name='scouted', aliases=['scdone','scend'],help='End scouting.')
async def scoutend(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(time,legacy)
    time=0
    l=parm[1]
    stb=parm[2]
    if stb==0:
        await update_sheet(world,"Scouted",time,l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")


@bot.command(name='start', aliases=['begin','run','go'],help='Start train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def begintrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]
    stb=parm[2]

    if stb==0:
        await update_sheet(world,"Running",time,l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")


@bot.command(name='end', aliases=['done','dead','finish'],help='Finish train.\n Time parameter is optional, defaults to current time and can be manually set in form "+15" (minutes) or "15:24" (server time)')
async def endtrain(ctx, world, time=None, legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(time,legacy)
    time=parm[0]
    l=parm[1]
    stb=parm[2]
    if stb==0:
        await update_sheet(world,"Dead",time,l)
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❓")
    if conf["sonar"]["enable"]==True:    
        # statistics 
        sel_stat="""
    SELECT round(avg(players)),min(players),max(players) from hunt 
    INNER JOIN hunts on hunts.id = hunt.huntid 
    INNER JOIN worlds on worlds.id=hunt.worldid 
    WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND currenthp=0 AND lastkilled > datetime('now', '-45 minutes') AND players>10
                """

        if l==0:
            exp=5
        else:
            exp=4

        cursor.execute(sel_stat,(exp, world))
        stats=cursor.fetchall()[0]
        s_avg=stats[0]
        s_min=stats[1]
        s_max=stats[2]
        
        await scout_log(f"Average participation on the train seemed to be at least {s_avg} players. (varied between {s_min}-{s_max})")

@bot.command(name="status", aliases=['getstatus','stat'],help='Get train status')
async def getstatus(ctx, legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    
    leg=0
    if legacy[0].capitalize() == "L":
        leg=1
    msg=await update_from_sheets_to_chat(leg)
    await ctx.send(msg)
    await ctx.message.add_reaction("✅")

@bot.command(name="cstatus", aliases=['compactstatus','cstat','cs'],help='Get compact train status')
async def getstatus(ctx):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    
    msg=await update_from_sheets_to_compact_chat()
    await ctx.send(msg)
    await ctx.message.add_reaction("✅")

async def periodicstatus():
    """Get statuses for different servers and log them on bot log channel. This is run from StatusLoop every 5 minutes."""
    
    msg=await update_from_sheets_to_chat(0)
    await bot_log(msg)
    msg=await update_from_sheets_to_chat(1)
    await bot_log(msg)

async def post_webhooks(msg, expansion):
    """Send a message using webhook to multiple Discord servers."""
    logging.debug("post_webhooks start")
    for w in conf["webhooks"]:
        wh=w["webhook"]
        r=w["roles"][expansion]
        if r!=0:
            rtxt=""
            if r>1:
                rtxt=f"<@&{r}> "                
            logging.debug(f'Sending to {w["name"]}')
            msgtxt=f"{rtxt}{msg}"
            async with aiohttp.ClientSession() as session:
                webhook=discord.Webhook.from_url(w["webhook"], session=session)
                try:
                    await webhook.send(content=msgtxt,username="Nunyunuwi",avatar_url="https://jvaarani.kapsi.fi/nuny.png")                        
                except discord.errors.HTTPException as e:
                    logging.error(f'Unable to send message to {w["name"]}: {e}')
                    pass

@bot.command(name="advertise", aliases=['ad','shout','sh'],help='Advertise your train. Put multi-part parameters in quotes (eg. .shout twin "Fort Jobb"). Additionally will set the server status to running.')
async def advertise(ctx, world, start, legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    username=ctx.message.author.display_name

    if len(start)<6:
        await ctx.message.add_reaction("❌")
        await ctx.send("Start location needs to be over 5 characters.")
        return

    tenmin=datetime.timedelta(minutes=10)+datetime.datetime.now()
    timestamp=int(mktime(tenmin.timetuple()))

    try:
        world=parse_world(world)
    except ValueError:
        await ctx.message.add_reaction("❓")
        await ctx.send("Invalid world.")
        return()

    parm=parse_parameters(None,legacy)
    l=parm[1]
    stb=parm[2]
    if l==0:
        msg=f"About to send this notification to various servers: ```@Endwalker_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if l==1:
        msg=f"About to send this notification to various servers: ```@Shadowbringers_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```Also I will set the server to *running* state. React with ✅ to send or wait 30 seconds to cancel."
    if stb==1:
        msg=f"About to send this notification to various servers: ```@Stormblood_role **[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."
 
    msg1=await ctx.send(msg)
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug("Timed out while waiting for reaction.")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user=res
            logging.debug(reaction.emoji)

    expansion=6
    if l==1:
        expansion=5
    if stb==1:
        expansion=4
     
    msg=f"**[{world}]** Hunt train starting <t:{timestamp}:R> at {start} (Conductor: {username})."
    await post_webhooks(msg,expansion)
    
    time=parm[0]
    if stb==0: 
        await update_sheet(world,"Running",time,l)

    await msg1.delete()
    await ctx.message.add_reaction('✅')

@bot.command(name="advmanual", aliases=['adm','mshout','msh'],help='Advertise your train. Put multi-part parameters in quotes (eg. .mshout "[Twintania] Hunt train starting in 10 minutes at Fort Jobb")')
async def madvertise(ctx, message, legacy="0"):
    if ctx.channel.id != conf["discord"]["channels"]["bot"]:
        return
    username=ctx.message.author.display_name
    await bot_log(f"{ctx.message.author.display_name}: {ctx.message.content}")
    
    if len(message)<6:
        await ctx.message.add_reaction("❌")
        await ctx.send("Message needs to be over 5 characters.")
        return

    parm=parse_parameters(None,legacy)
    l=parm[1]
    stb=parm[2]
    if l==0:
        msg=f"About to send this notification to various servers: ```@Endwalker_role {message} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."
    if l==1:
        msg=f"About to send this notification to various servers: ```@Shadowbringers_role {message} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."
    if stb==1:
        msg=f"About to send this notification to various servers: ```@Stormblood_role {message} (Conductor: {username}).```React with ✅ to send or wait 30 seconds to cancel."

    msg1=await ctx.send(msg)
    await msg1.add_reaction("✅")

    def check(reaction, user):
        return reaction.message.id==msg1.id and str(reaction.emoji)=='✅' and user.id == ctx.author.id

    try:
        res=await bot.wait_for("reaction_add", check=check,timeout=30)
    except asyncio.TimeoutError:
        logging.debug ("Timed out while waiting for reaction.")
        await msg1.delete()
        await ctx.message.add_reaction('❌')
        pass
    else:
        if res:
            reaction, user=res
            logging.debug (reaction.emoji)

    expansion=6
    if l==1:
        expansion=5
    if stb==1:
        expansion=4
     
    msg=f"{message} (Conductor: {username})."
    await post_webhooks(msg,expansion)

    await msg1.delete()
    await ctx.message.add_reaction('✅')
    if stb!=1:
        await scout_log("Please set the server running manually if needed.")

@tasks.loop(seconds = 60)
async def STLoop():
    now=datetime.datetime.strftime(datetime.datetime.utcnow(),"%H:%M")
    if ready == 1:
        await bot.change_presence(activity=discord.Game(f"Server time: {now}"))

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

if conf["sonar"]["enable"]==True:

    # sonar stuff init
    conn = sqlite3.connect('hunt.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    cursor=conn.cursor()

    # we're interested in light dc

    dc=("Light",)
    sel="SELECT worlds.id from worlds INNER JOIN dcs ON worlds.datacenterid = dcs.id WHERE dcs.name = ?"
    cursor.execute(sel,dc)
    r=cursor.fetchall()

    worldidlist=[]
    for w in r:
        worldidlist.append(w[0])

    # we're interested in A-rank hunts

    cursor.execute('SELECT id from hunts WHERE rank=2')
    r=cursor.fetchall()

    huntidlist=[]
    for h in r:
        huntidlist.append(h[0])

    # SHB+ A-rank hunts for snipe notifications

    cursor.execute('SELECT id from hunts WHERE rank=2 AND expansion>=4')
    r=cursor.fetchall()

    huntidlist_nuts=[]
    for h in r:
        huntidlist_nuts.append(h[0])

    # S-rank list for special purposes

    cursor.execute('SELECT id from hunts WHERE rank=3')
    r=cursor.fetchall()

    huntidlist_s=[]
    for h in r:
        huntidlist_s.append(h[0])

    check="""SELECT 
        key, huntid, worldid, 
        zoneid, instanceid, players, 
        currenthp, maxhp, lastseen, 
        lastfound, lastkilled, lastupdated, 
        lastuntouched,actorid,status,x,y
        FROM 'hunt' WHERE key = ?"""
    ins="""INSERT OR REPLACE INTO 'hunt' (
        key, huntid, worldid, 
        zoneid, instanceid, players, 
        currenthp, maxhp, lastseen, 
        lastfound, lastkilled, lastupdated, 
        lastuntouched,actorid,status,x,y) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

def relay_to_sql(msg,status):
    return (msg['Relay']['Key'],
       msg['Relay']['Id'],
       msg['Relay']['WorldId'],
       msg['Relay']['ZoneId'],
       msg['Relay']['InstanceId'],
       msg['Relay']['Players'],
       msg['Relay']['CurrentHp'],
       msg['Relay']['MaxHp'],
       msg['LastSeen'],
       msg['LastFound'],
       msg['LastKilled'],
       msg['LastUpdated'],
       msg['LastUntouched'],
       msg['Relay']['ActorId'],
       status,
       msg['Relay']['Coords']['X'],
       msg['Relay']['Coords']['Y']
)
    
def sql_to_relay(sql):
    r={}
    r['Key']=sql[0]
    r['Id']=sql[1]
    r['WorldId']=sql[2]
    r['ZoneId']=sql[3]
    r['InstanceId']=sql[4]
    r['Players']=sql[5]
    r['CurrentHp']=sql[6]
    r['MaxHp']=sql[7]
    r['LastSeen']=sql[8]
    r['LastFound']=sql[9]
    r['LastKilled']=sql[10]
    r['LastUpdated']=sql[11]
    r['LastUntouched']=sql[12]
    r['ActorId']=sql[13]
    r['Status']=sql[14]
    r['x']=sql[15]
    r['y']=sql[16]
    return (r)    


async def huntname(msg):
    expansions={1: 'ARR',
                2: 'HW',
                3: 'STB',
                4: 'SHB',
                5: 'EW'}
    instances={0: '',
               1: ' (1)',
               2: ' (2)',
               3: ' (3)'}
    sel="SELECT name,expansion FROM hunts WHERE id = ?"
    h=cursor.execute(sel,(msg["Relay"]["Id"],)).fetchone()
    sel="SELECT name FROM worlds WHERE id = ?"
    w=cursor.execute(sel,(msg["Relay"]["WorldId"],)).fetchone()
    return ({'exp': expansions[h[1]],
             'world': w[0],
             'name': h[0],
             'instance': instances[int(msg["Relay"]["InstanceId"])]})


@tasks.loop(count=None)
async def websocketrunner():
    while True:
        try:
            async with connect(conf["sonar"]["websocket"]) as websocket:
                while True:
                    try:
                        s_msg = json.loads(await websocket.recv())
                        if (s_msg["Relay"]["Type"]=="Hunt"):
                            if (s_msg["Relay"]["WorldId"] in worldidlist):
                                if (s_msg["Relay"]["Id"] in huntidlist):
                                    s_msg["LastSeen"]=datetime.datetime.utcfromtimestamp(s_msg["LastSeen"]/1000)
                                    s_msg["LastFound"]=datetime.datetime.utcfromtimestamp(s_msg["LastFound"]/1000)
                                    s_msg["LastKilled"]=datetime.datetime.utcfromtimestamp(s_msg["LastKilled"]/1000)
                                    s_msg["LastUpdated"]=datetime.datetime.utcfromtimestamp(s_msg["LastUpdated"]/1000)
                                    s_msg["LastUntouched"]=datetime.datetime.utcfromtimestamp(s_msg["LastUntouched"]/1000)
                                    
                                    h=cursor.execute(check,(s_msg["Relay"]["Key"],)).fetchone()
                                    if h==None:
                                        d=await huntname(s_msg)
                                        await sonar_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} spotted first time after database refresh at {int((s_msg["Relay"]["CurrentHp"]/s_msg["Relay"]["MaxHp"])*100)}% HP.')                                    
                                        status=1
                                        if s_msg["LastUpdated"]==s_msg["LastUntouched"]:
                                            status=2
                                    else: 
                                        status=0
                                        h=sql_to_relay(h)   
                                        status=h["Status"]
                                        # actorid changed -> new sighting
                                        if (h["ActorId"] != s_msg["Relay"]["ActorId"]):
                                            d=await huntname(s_msg)
                                            await sonar_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} spotted with a new actor id at {int((s_msg["Relay"]["CurrentHp"]/s_msg["Relay"]["MaxHp"])*100)}% HP.')
                                            status=1
                                            if s_msg["LastUpdated"]==s_msg["LastUntouched"]:
                                                # untouched
                                                status=2
                                        if ((s_msg["LastUpdated"]-s_msg["LastUntouched"]).total_seconds()>15 and status!=1):
                                            status=1
                                            d=await huntname(s_msg)
                                            await sonar_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} has been pulled and is at {int((s_msg["Relay"]["CurrentHp"]/s_msg["Relay"]["MaxHp"])*100)}% HP. ({s_msg["Relay"]["Players"]} players nearby)')
                                        if (s_msg["LastUpdated"]==s_msg["LastUntouched"] and status==1):
                                            status=2
                                            d=await huntname(s_msg)
                                            await sonar_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was reset ({s_msg["Relay"]["Players"]} players nearby).')
                                        if (s_msg["Relay"]["CurrentHp"]==0 and status != 0):
                                            status=0
                                            d=await huntname(s_msg)
                                            await sonar_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was killed ({s_msg["Relay"]["Players"]} players nearby).')
                                            if (s_msg["Relay"]["Players"]<10 and s_msg["Relay"]["Id"] in huntidlist_nuts):
                                                await scout_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was killed ({s_msg["Relay"]["Players"]} players nearby). (SNIPE?)')
                                    h=relay_to_sql(s_msg,status)
                                    cursor.execute(ins,h)
                                if (s_msg["Relay"]["Id"] in huntidlist_s):
                                    s_msg["LastSeen"]=datetime.datetime.utcfromtimestamp(s_msg["LastSeen"]/1000)
                                    s_msg["LastFound"]=datetime.datetime.utcfromtimestamp(s_msg["LastFound"]/1000)
                                    s_msg["LastKilled"]=datetime.datetime.utcfromtimestamp(s_msg["LastKilled"]/1000)
                                    s_msg["LastUpdated"]=datetime.datetime.utcfromtimestamp(s_msg["LastUpdated"]/1000)
                                    s_msg["LastUntouched"]=datetime.datetime.utcfromtimestamp(s_msg["LastUntouched"]/1000)
                                    
                                    h=cursor.execute(check,(s_msg["Relay"]["Key"],)).fetchone()
                                    if h==None:
                                        d=await huntname(s_msg)
                                        logging.info(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} spotted first time after database refresh at {int((s_msg["Relay"]["CurrentHp"]/s_msg["Relay"]["MaxHp"])*100)}% HP.')                                    
                                        status=1
                                        if s_msg["LastUpdated"]==s_msg["LastUntouched"]:
                                            status=2
                                    else: 
                                        status=0
                                        h=sql_to_relay(h)   
                                        status=h["Status"]
                                        # actorid changed -> new sighting
                                        if (h["ActorId"] != s_msg["Relay"]["ActorId"]):
                                            d=await huntname(s_msg)
                                            logging.info(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} spotted with a new actor id at {int((s_msg["Relay"]["CurrentHp"]/s_msg["Relay"]["MaxHp"])*100)}% HP.')
                                            status=1
                                            if s_msg["LastUpdated"]==s_msg["LastUntouched"]:
                                                # untouched
                                                status=2
                                        if ((s_msg["LastUpdated"]-s_msg["LastUntouched"]).total_seconds()>15 and status!=1):
                                            status=1
                                            d=await huntname(s_msg)
                                            logging.info(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} has been pulled and is at {int((s_msg["Relay"]["CurrentHp"]/s_msg["Relay"]["MaxHp"])*100)}% HP. ({s_msg["Relay"]["Players"]} players nearby)')
                                            if (s_msg["Relay"]["Players"]<10):
                                                await spec_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} has been pulled and is at {int((s_msg["Relay"]["CurrentHp"]/s_msg["Relay"]["MaxHp"])*100)}% HP. ({s_msg["Relay"]["Players"]} players nearby) (SNIPE?)')
                                        if (s_msg["LastUpdated"]==s_msg["LastUntouched"] and status==1):
                                            status=2
                                            d=await huntname(s_msg)
                                            logging.info(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was reset ({s_msg["Relay"]["Players"]} players nearby).')
                                            if (s_msg["Relay"]["Players"]<10):
                                                await spec_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was reset ({s_msg["Relay"]["Players"]} players nearby). (SNIPE?)')
                                        if (s_msg["Relay"]["CurrentHp"]==0 and status != 0):
                                            status=0
                                            d=await huntname(s_msg)
                                            logging.info(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was killed ({s_msg["Relay"]["Players"]} players nearby).')
                                            if (s_msg["Relay"]["Players"]<10):
                                                await spec_log(f'{d["exp"]}: [{d["world"]}] {d["name"]}{d["instance"]} was killed ({s_msg["Relay"]["Players"]} players nearby). (SNIPE?)')
                                    h=relay_to_sql(s_msg,status)
                                    cursor.execute(ins,h)
                                    
                    except KeyError as errori:
                        logging.error(f"Got a KeyError in websocketrunner: {errori}")
                        pass
                    conn.commit()
        except websockets.exceptions.WebSocketException as errori:
            logging.error (f"Socket error in websocketrunner: {errori}")
        await asyncio.sleep(30)

@bot.event
async def on_ready():
    global ready
    logging.info(f'{bot.user} has connected to Discord!')
    ready=1
    SheetLoop.start()
    STLoop.start()
    StatusLoop.start()
    if conf["sonar"]["enable"]==True:
        websocketrunner.start()

async def main():         
    async with bot:
        await bot.start(conf["discord"]["token"])

asyncio.run(main())
