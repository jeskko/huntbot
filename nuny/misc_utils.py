import datetime
import nuny.config

import nuny.discord_utils

from nuny.sheet_utils import worldStatusLoc,worldTimeLoc,fetch_sheet,update_from_sheets_to_chat
from nuny.sonar import sonar_speculate,sonar_mapping
from nuny.log_utils import bot_log

def parse_world(world):
    """
    Convert text input to world name useable on various functions. 
    Really simple, uses only the first letter of the input to figure out which world it is. Works on Light DC but on datacenters with overlapping initial letters this would be a problem.
    Raises ValueError in case of invalid world being tried to be parsed.
    """
    
    initial=world[0].lower()
    w=[w for w in nuny.config.conf["worlds"] if w["initial"]==initial]
    try:
        name=w[0]["name"]
    except IndexError:
        raise ValueError("Invalid world")
    return name
        
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
    if nuny.config.conf["sonar"]["enable"]==True:
        msg+=sonar_speculate(w,l)
    return msg

def mapping(world,legacy=None):
    """Fetches mapping data estimate from Sonar."""
    if nuny.config.conf["sonar"]["enable"]==True:
        
        try:
            w=parse_world(world)
        except ValueError:
            return("Invalid world.")  
        msg=sonar_mapping(w,legacy)
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

async def periodicstatus():
    """Get statuses for different servers and log them on bot log channel. This is run from StatusLoop every 5 minutes."""
    
    msg=await update_from_sheets_to_chat(0)
    await bot_log(msg)
    msg=await update_from_sheets_to_chat(1)
    await bot_log(msg)

