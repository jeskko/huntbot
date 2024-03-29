#!/usr/bin/env python3

# this assumes that db has been initialized and assets are up to date
import json,sqlite3,yaml
from urllib.request import urlopen,Request
from datetime import datetime

with open('config.yaml','r') as file:
    conf=yaml.safe_load(file)

if conf["sonar"]["enable"]==False:
    exit()
    
conn = sqlite3.connect('hunt.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
cursor=conn.cursor()

with urlopen(Request(conf["sonar"]["bootstrap"], headers={'User-Agent': 'Nunyunuwi'})) as url:
    hunts=json.load(url)
    
ins="""INSERT OR REPLACE INTO 'hunt' (
    key, huntid, worldid, 
    zoneid, instanceid, players, 
    currenthp, maxhp, lastseen, 
    lastfound, lastkilled, lastupdated, 
    lastuntouched,actorid,status,x,y) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    
def relay_to_sql(msg):
    return (msg['relay']['Key'],
       msg['relay']['id'],
       msg['relay']['worldId'],
       msg['relay']['zoneId'],
       msg['relay']['instanceId'],
       msg['relay']['players'],
       msg['relay']['currentHp'],
       msg['relay']['maxHp'],
       datetime.utcfromtimestamp(msg['lastSeen']/1000),
       datetime.utcfromtimestamp(msg['lastFound']/1000),
       datetime.utcfromtimestamp(msg['lastKilled']/1000),
       datetime.utcfromtimestamp(msg['lastUpdated']/1000),
       datetime.utcfromtimestamp(msg['lastUntouched']/1000),
       msg['relay']['actorId'],
       0,
       msg['relay']['coords']['x'],
       msg['relay']['coords']['y']
       )
     
for h in hunts.values():
    cursor.execute(ins,(relay_to_sql(h)))

conn.commit()
    