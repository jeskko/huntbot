import datetime
import logging
import nuny.config

import nuny.discord_utils
import nuny.db_utils

from nuny.sonar import sonar_speculate,sonar_mapping
from nuny.log_utils import bot_log

def set_status(world,status,expansion,time):
    return

def get_status(world,expansion):
    return

def parse_world(world):
    """
    Convert text input to world name useable on various functions. 
    Raises ValueError in case of invalid world being tried to be parsed.
    """
    
    wl=world.lower()
    w=[w for w in nuny.config.conf["channels"]["worlds"] if w["name"].lower()[0:len(wl)]==wl]
    try:
        name=w[0]["name"]
    except IndexError:
        raise ValueError("Invalid world")
    if len(w)>1:
        raise ValueError("Ambiguous world")
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

def speculate(world,expansion):
    """
    Speculate about hunt marks and their spawn/despawn status.
    https://cdn.discordapp.com/attachments/884351171668619265/972159569658789978/unknown.png
    Also checks Sonar data about the selected world.
    """
    now=datetime.datetime.utcnow()
    
    try:
        w=parse_world(world)
    except ValueError:
        return("Invalid world.")

    status,time=nuny.db_utils.getstatus(w,expansion)
    delta=now-time

    msg=f"Status **{status}** for **{w}** {expansion}.0 was set at {time}.\n"
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
        msg+=sonar_speculate(w,expansion)
    return msg

def mapping(world,expansion):
    """Fetches mapping data estimate from Sonar."""
    if nuny.config.conf["sonar"]["enable"]==True:
        
        try:
            w=parse_world(world)
        except ValueError:
            return(f"Invalid world {world}.")  
        msg=sonar_mapping(w,expansion)
    else:
        msg="Sonar is disabled for this bot, unable to do mapping."
    return msg
 
def parse_parameters(time,expansion):
    """
    Tries to sanitize time and legacy parameters given on a bot command.
    Will raise ValueError if input is incoherent.
    """
    if time==None:
            time=datetime.datetime.utcnow()
    else:
        if time.len()==1:
            try: 
                exp=int(time)
            except:
                raise ValueError("Invalid non-numeric expansion")                  
        else:
            try:
                if time[0]=="+":
                    time=datetime.timedelta(minutes=int(time[1:]))+datetime.datetime.utcnow()
                else:
                    t=time.split(":")
                    h=int(t[0])
                    m=int(t[1])
                    time=datetime.datetime.utcnow().replace(hour=h,minute=m,second=45)
            except ValueError:
                raise ValueError("Invalid time value")
            try:
                exp=int(expansion)
            except:
                raise ValueError("Invalid non-numeric expansion")
            if (exp<2 or exp>7):
                raise ValueError("Invalid expansion")
    return [time,exp]        

async def periodicstatus():
    """Get statuses for different servers and log them on bot log channel. This is run from StatusLoop every 5 minutes."""
    
    msg="DT statusviesti tähän"
    await bot_log(msg)
    msg="EW statusviesti tähän"
    await bot_log(msg)

async def update_messages():
    """Update status messages on different world channels."""
    for expansion in [5,6,7]:
        for world in nuny.config.conf["channels"]["worlds"]:
            name=world["name"]
            msg=speculate(name,expansion)+"\n\n"+mapping(name,expansion)
            await nuny.discord_utils.update_message(name,expansion,msg)


async def update_channels():
    """Fetch data db and update channel names."""
    for w in nuny.config.conf["channels"]["worlds"]:
        world=w["name"]
        s_world=w["short"]
        for e in w["channels"].items():
            exp=e[0]
            chan=e[1]
            status,time=nuny.db_utils.getstatus(world,exp)
            await update_channel(chan,s_world,status)
    print("update channels done")

async def update_channel(chan,s_name,status):
    """Update channel name value. Will check if actual update is necessary to avoid rate limiting."""
    
    try:
        st=[st for st in nuny.config.conf["statuses"] if st["name"]==status][0]
    except IndexError:
        raise ValueError(f"Invalid world status {status}.")
    newname=f'{st["icon"]}{s_name}-{st["short"]}'
    
    chan=nuny.discord_utils.bot.get_channel(chan) 
    if chan.name != newname:
        logging.debug(f"Updating channel name from {chan.name} to {newname}.")
        await chan.edit(name=newname)
    else:
        logging.debug("no need to update channel name.")