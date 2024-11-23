import datetime
import logging
from tabulate import tabulate


import nuny.config
import nuny.discord_utils
import nuny.db_utils


from nuny.sonar import sonar_speculate,sonar_mapping
from nuny.log_utils import bot_log

async def groundskeeper():
    # check all statuses and update if timers say so
    for w in nuny.config.conf["worlds"]:
        for expansion in range(5,8):
            n=w["name"]
            (status,time)=nuny.db_utils.getstatus(n,expansion)
            td=datetime.datetime.utcnow()-time
            if status=="Dead" and td>datetime.timedelta(hours=6):
                nuny.db_utils.setstatus(n,expansion,"Up",time+datetime.timedelta(hours=6))
                logging.info(f"{n} {expansion}.0 changed to up.")
            if status=="Rebooted" and td>datetime.timedelta(hours=3,minutes=36):
                nuny.db_utils.setstatus(n,expansion,"Up",time+datetime.timedelta(hours=3,minutes=36))
                logging.info(f"{n} {expansion}.0 changed to up.")
            if status=="Running" and td>datetime.timedelta(hours=1,minutes=30):
                nuny.db_utils.setstatus(n,expansion,"Dead",time+datetime.timedelta(hours=1))
                logging.info(f"{n} {expansion}.0 changed to dead, someone forgot to end their train.")
                
async def dailycleanup():
    r=nuny.db_utils.cleanup()
    logging.info(f"Daily cleanup done, {r} statuses that were over week old were removed.")
                  
def set_status(world,status,expansion,time=None):  
    """
    Update status for a server. use "last" as time parameter to use the timestamp of last status (will be incremented by 1 second so sorting works properly).
    If status was "Dead" or "Rebooted" and "last" was used as time parameter, adjust the time to reflect when the server would have been actually up
    """
    if expansion in range(5,8):
        if time=="last":
            time,expansion=parse_parameters(None,expansion)
            (s,time)=nuny.db_utils.getstatus(world,expansion)
            time=time+datetime.timedelta(seconds=1)
            if s=="Dead":
                time=time+datetime.timedelta(hours=6)
            if s=="Rebooted":
                time=time+datetime.timedelta(hours=3,minutes=36)
        else:
            time,expansion=parse_parameters(time,expansion)
                
        logging.info(f"Setting status for world {world} {expansion}.0 to {status} at {time}.")
        nuny.db_utils.setstatus(world,expansion,status,time)
    else:
        raise ValueError("Untracked expansion")
    return

def process_despawn(status,time):
    td=datetime.datetime.utcnow()-time
    ts=td.total_seconds()
    if status=="Dead":
        # spawn window starts at 3.5 hours (presuming that train takes 30 minutes)
        if ts>12600:
            status="Spawning"

    if status=="Rebooted":
        # spawn window starts at 2.4 hours after maintenance reboot
        if ts>8640:
            status="Spawning"
            
    if status=="Up":
        for d in nuny.config.conf["despawn"]:
            if ts>=d["start"] and ts<d["end"]:
                status=d["status"]
    return status        

def get_statuses(expansion):
    message=f"{expansion}.0 status:\n```"
    table=[]
    table.append(["Server","Status\nchanged","Status\nduration","Status"])
    for w in nuny.config.conf["worlds"]:
        (status,time)=nuny.db_utils.getstatus(w["name"],expansion)
        status=process_despawn(status,time)
        if status=="Unknown":
            t1=""
        else:
            t1=datetime.datetime.strftime(time,"%d.%m %H:%M")
        t2_td=datetime.datetime.utcnow()-time
        t2_h=int(divmod(t2_td.total_seconds(),3600)[0])
        t2_m=int(divmod(divmod(t2_td.total_seconds(),3600)[1],60)[0])
        if t2_h<0:
            t2=""
        else:
            if t2_h>168:
                t2="long"                
            else:
                t2=f"{t2_h}:{t2_m:02d}"
        table.append([w["name"],t1,t2,status])
    message+=tabulate(table,headers="firstrow",tablefmt="fancy_grid")+"```"        
    return message

def get_history(world,expansion):
    message=f"Last statuses for {world} {expansion}.0:\n```"
    table=[]
    table.append(["Id","Status","Timestamp"])
    for r in nuny.db_utils.gethistory(world,expansion):
        table.append(r)
    message+=tabulate(table,headers="firstrow",tablefmt="fancy_grid")+"```"        
    return message 

def maintenance_reboot(time):
    for w in nuny.config.conf["worlds"]:
       for e in range(5,8):
           nuny.db_utils.setstatus(w["name"],e,"Rebooted",time)

def parse_world(world):
    """
    Convert text input to world name useable on various functions. 
    Raises ValueError in case of invalid world being tried to be parsed.
    """
    
    wl=world.lower()
    w=[w for w in nuny.config.conf["worlds"] if w["name"].lower()[0:len(wl)]==wl]
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
    if status=="Rebooted":
        msg+=spec_delta(time,8640,12960,"spawn")        
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

            if expansion==None:
                exp=nuny.config.conf["def_exp"]
            else:
                exp=expansion
    else:
        if len(time)==1:
            try: 
                exp=int(time)
            except:
                raise ValueError("Invalid non-numeric expansion")    
            time=datetime.datetime.utcnow()              
        else:
            try:
                if time[0]=="+":
                    time=datetime.timedelta(minutes=int(time[1:]))+datetime.datetime.utcnow()
                else:
                    if time[0]=="-":
                        time=datetime.timedelta(minutes=-int(time[1:]))+datetime.datetime.utcnow()     
                    else:              
                        t=time.split(":")

                        if len(t)==2:
                            h=int(t[0])
                            m=int(t[1][0:2])
                            time=datetime.datetime.utcnow().replace(hour=h,minute=m,second=45)
                            if len(t[1])==4:
                                if t[1][2]=="-":
                                    time=datetime.timedelta(days=-int(t[1][3]))+time
                                if t[1][2]=="+":
                                    time=datetime.timedelta(days=int(t[1][3]))+time
                        else:
                            raise ValueError("Invalid time value")
            except ValueError:
                raise ValueError("Invalid time value")
            if expansion==None:
                expansion=nuny.config.config["def_exp"]
            try:
                exp=int(expansion)
            except:
                raise ValueError("Invalid non-numeric expansion")
            if (exp<2 or exp>7):
                raise ValueError("Invalid expansion")
    return (time,exp) 

async def periodicstatus():
    """Get statuses for different servers and log them on bot log channel. This is run from StatusLoop every 5 minutes."""
    
    msg=get_statuses(7)
    await bot_log(msg)
    msg=get_statuses(6)
    await bot_log(msg)
    msg=get_statuses(5)
    await bot_log(msg)
    

async def update_messages():
    """Update status messages on different world channels."""
    for expansion in [5,6,7]:
        for world in nuny.config.conf["worlds"]:
            name=world["name"]
            msg=speculate(name,expansion)+"\n\n"+mapping(name,expansion)
            await nuny.discord_utils.update_message(name,expansion,msg)


async def update_channels():
    """Fetch data db and update channel names."""
    for w in nuny.config.conf["worlds"]:
        world=w["name"]
        s_world=w["short"]
        for e in w["channels"].items():
            exp=e[0]
            chan=e[1]
            status,time=nuny.db_utils.getstatus(world,exp)
            status=process_despawn(status,time)
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