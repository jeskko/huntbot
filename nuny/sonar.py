import websockets.exceptions
import json
import datetime
import logging
import asyncio
from discord.ext import tasks
from websockets.client import connect

import nuny.config
import nuny.db_utils
from nuny.log_utils import sonar_log,scout_log,spec_log

worldidlist = None
huntidlist = None
huntidlist_nuts = None
huntidlist_s = None
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
                5: 'EW',
                6: 'DT'}
    instances={0: '',
               1: ' (1)',
               2: ' (2)',
               3: ' (3)',
               4: ' (4)',
               5: ' (5)',
               6: ' (6)'}
    sel="SELECT name,expansion FROM hunts WHERE id = ?"
    h=nuny.db_utils.cursor.execute(sel,(msg["Relay"]["Id"],)).fetchone()
    sel="SELECT name FROM worlds WHERE id = ?"
    w=nuny.db_utils.cursor.execute(sel,(msg["Relay"]["WorldId"],)).fetchone()
    return ({'exp': expansions[h[1]],
             'world': w[0],
             'name': h[0],
             'instance': instances[int(msg["Relay"]["InstanceId"])]})

def sonar_speculate(w,exp):
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

    exp=exp-1
    
    nuny.db_utils.cursor.execute(sel_alive,(exp, w))
    alive=nuny.db_utils.cursor.fetchall()[0][0]

    nuny.db_utils.cursor.execute(sel_despawn,(exp, w))
    despawn=nuny.db_utils.cursor.fetchall()[0][0]
    
    nuny.db_utils.cursor.execute(sel_spawned,(exp, w))
    spawned=nuny.db_utils.cursor.fetchall()[0][0]

    nuny.db_utils.cursor.execute(sel_spawning,(exp, w))
    spawning=nuny.db_utils.cursor.fetchall()[0][0]
    
    nuny.db_utils.cursor.execute(sel_dead,(exp, w))
    dead=nuny.db_utils.cursor.fetchall()[0][0]

    return f"\nSonar data suggests that {alive} marks are alive, {spawned} marks should have spawned, {despawn} marks might have already despawned, {spawning} marks have potential to spawn and {dead} marks are dead."

def init_sonar():
    global worldidlist, huntidlist, huntidlist_nuts, huntidlist_s
    if nuny.config.conf["sonar"]["enable"]==True:

        # sonar stuff init


        # we're interested in light dc

        dc=("Light",)
        sel="SELECT worlds.id from worlds INNER JOIN dcs ON worlds.datacenterid = dcs.id WHERE dcs.name = ?"
        nuny.db_utils.cursor.execute(sel,dc)
        r=nuny.db_utils.cursor.fetchall()

        worldidlist=[]
        for w in r:
            worldidlist.append(w[0])

        # we're interested in A-rank hunts

        nuny.db_utils.cursor.execute('SELECT id from hunts WHERE rank=2')
        r=nuny.db_utils.cursor.fetchall()

        huntidlist=[]
        for h in r:
            huntidlist.append(h[0])

        # SHB+ A-rank hunts for snipe notifications

        nuny.db_utils.cursor.execute('SELECT id from hunts WHERE rank=2 AND expansion>=4')
        r=nuny.db_utils.cursor.fetchall()

        huntidlist_nuts=[]
        for h in r:
            huntidlist_nuts.append(h[0])

        # S-rank list for special purposes

        nuny.db_utils.cursor.execute('SELECT id from hunts WHERE rank=3')
        r=nuny.db_utils.cursor.fetchall()

        huntidlist_s=[]
        for h in r:
            huntidlist_s.append(h[0])


def sonar_mapping(w,expansion=7):
    try:
        exp=int(expansion)
    except:
        raise ValueError("Invalid non-numeric expansion")
    if (exp<2 or exp>7):
                raise ValueError("Invalid expansion")
    
    
    ishort={0: '',
            1: '',
            2: '',
            3: '',
            4: '',
            5: '',
            6: ''}
    
    ilong={0: '',
        1: '  (I1)',
        2: '  (I2)',
        3: '  (I3)',
        4: '  (I4)',
        5: '  (I5)',
        6: '  (I6)'}
    
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
    nuny.db_utils.cursor.execute(sel,(exp-1,w))
    h=nuny.db_utils.cursor.fetchall()
    msg="Sonar data suggests following mapping:\n```\n"
    for l in h:
        msg+=f"({l[0]}) {l[1]}{ishort[l[2]]} ( {l[3]} , {l[4]} ){ilong[l[2]]}\n"
    msg+="```"
    return msg

def sonar_health(w,expansion=7):
    try:
        exp=int(expansion)
    except:
        raise ValueError("Invalid non-numeric expansion")
    if (exp<2 or exp>7):
                raise ValueError("Invalid expansion")
    
    
    ishort={0: '',
            1: '',
            2: '',
            3: '',
            4: '',
            5: '',
            6: ''}
    
    ilong={0: '',
        1: '  (I1)',
        2: '  (I2)',
        3: '  (I3)',
        4: '  (I4)',
        5: '  (I5)',
        6: '  (I6)'}
    
    sel="""
SELECT hunts.name, zones.name,hunt.instanceid, 
    round(((41 / zones.scale) * (((hunt.x + zones.offset_x)*zones.scale + 1024) / 2048)+1),1),
    round(((41 / zones.scale) * (((hunt.y + zones.offset_y)*zones.scale + 1024) / 2048)+1),1), lastseen from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
INNER JOIN zones on zones.id=hunt.zoneid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND lastseen > datetime('now','-20 hours') AND lastfound > datetime('now','-20 hours') AND currenthp != 0
ORDER BY hunt.zoneid,hunt.instanceid
        """
    nuny.db_utils.cursor.execute(sel,(exp-1,w))
    h=nuny.db_utils.cursor.fetchall()
    msg="Sonar data suggests following hunt health status:\n```\n"
    for l in h:
        td=datetime.datetime.utcnow()-l[5]
        td_h=td.seconds//3600
        td_m=(td.seconds//60%60)
        msg+=f"{l[0]}: last seen {td_h:02d}:{td_m:02d} ago{ilong[l[2]]}\n"
    msg+="```"
    return msg
        
def sonarreset(timestamp):
    sel="""
DELETE FROM hunt 
WHERE lastfound < ?
    """
    nuny.db_utils.cursor.execute(sel,(timestamp,))
    return nuny.db_utils.cursor.rowcount
        
def sonar_stats(world,exp):
    # statistics 
    sel_stat="""
SELECT round(avg(players)),min(players),max(players) from hunt 
INNER JOIN hunts on hunts.id = hunt.huntid 
INNER JOIN worlds on worlds.id=hunt.worldid 
WHERE hunts.expansion=? AND hunts.rank=2 AND worlds.name=? AND currenthp=0 AND lastkilled > datetime('now', '-45 minutes') AND players>10
            """

    exp=exp-1
    
    nuny.db_utils.cursor.execute(sel_stat,(exp, world))
    stats=nuny.db_utils.cursor.fetchall()[0]
    s_avg=stats[0]
    s_min=stats[1]
    s_max=stats[2]
    return f"Average participation on the train seemed to be at least {s_avg} players. (varied between {s_min}-{s_max})"                
        
@tasks.loop(count=None)
async def websocketrunner():
    while True:
        try:
            async with connect(nuny.config.conf["sonar"]["websocket"]) as websocket:
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
                                    
                                    h=nuny.db_utils.cursor.execute(check,(s_msg["Relay"]["Key"],)).fetchone()
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
                                    nuny.db_utils.cursor.execute(ins,h)
                                if (s_msg["Relay"]["Id"] in huntidlist_s):
                                    s_msg["LastSeen"]=datetime.datetime.utcfromtimestamp(s_msg["LastSeen"]/1000)
                                    s_msg["LastFound"]=datetime.datetime.utcfromtimestamp(s_msg["LastFound"]/1000)
                                    s_msg["LastKilled"]=datetime.datetime.utcfromtimestamp(s_msg["LastKilled"]/1000)
                                    s_msg["LastUpdated"]=datetime.datetime.utcfromtimestamp(s_msg["LastUpdated"]/1000)
                                    s_msg["LastUntouched"]=datetime.datetime.utcfromtimestamp(s_msg["LastUntouched"]/1000)
                                    
                                    h=nuny.db_utils.cursor.execute(check,(s_msg["Relay"]["Key"],)).fetchone()
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
                                    nuny.db_utils.cursor.execute(ins,h)
                                    
                    except KeyError as errori:
                        logging.error(f"Got a KeyError in websocketrunner: {errori}")
                        pass
                    nuny.db_utils.conn.commit()
        except websockets.exceptions.WebSocketException as errori:
            logging.error (f"Socket error in websocketrunner: {errori}")
        await asyncio.sleep(30)
