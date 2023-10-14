#!/usr/bin/env python3

import sqlite3,json,os
from urllib.request import urlopen,Request
from dotenv import load_dotenv

load_dotenv()
DC_ASSET=os.getenv('DC_ASSET')
WORLD_ASSET=os.getenv('WORLD_ASSET')
HUNT_ASSET=os.getenv('HUNT_ASSET')
ZONE_ASSET=os.getenv('ZONE_ASSET')
REGION_ASSET=os.getenv('REGION_ASSET')

conn = sqlite3.connect('hunt.db')

cursor=conn.cursor()

with urlopen(Request(DC_ASSET, headers={'User-Agent': 'Nunyunuwi'})) as url:
     datacenter=json.load(url)
with urlopen(Request(WORLD_ASSET, headers={'User-Agent': 'Nunyunuwi'})) as url:
     world=json.load(url)
with urlopen(Request(HUNT_ASSET, headers={'User-Agent': 'Nunyunuwi'})) as url:
    hunt=json.load(url)
with urlopen(Request(ZONE_ASSET, headers={'User-Agent': 'Nunyunuwi'})) as url:
    zone=json.load(url)
with urlopen(Request(REGION_ASSET, headers={'User-Agent': 'Nunyunuwi'})) as url:
    region=json.load(url)
        
cursor.execute("DELETE FROM 'regions'")

ins=("INSERT INTO 'regions' ('id','name') VALUES (?, ?)")
for r in region.values():
    data=(r['Id'],r['Name'])
    cursor.execute(ins,data)
    
conn.commit()

cursor.execute("DELETE FROM 'dcs'")
ins=("INSERT INTO 'dcs' ('id','name','regionid') VALUES (?, ?, ?)")     
for r in datacenter.values():
    data=(r['Id'],r['Name'], r['RegionId'])
    cursor.execute(ins,data)
    
conn.commit()

cursor.execute("DELETE FROM 'worlds'")

ins=("INSERT INTO 'worlds' ('id','name','datacenterid','regionid') VALUES (?, ?, ?, ?)")        
for r in world.values():
    data=(r['Id'],r['Name'], r['DatacenterId'], r['RegionId'])
    cursor.execute(ins,data)
    
conn.commit()

cursor.execute("DELETE FROM 'zones'")

ins=("INSERT INTO 'zones' ('id','name','expansion','mapid','scale','offset_x','offset_y','offset_z') VALUES (?, ?, ?, ?, ?, ?, ?, ?)")        
for r in zone.values():
    try:
        data=(r['Id'],r['Name']['English'], r['Expansion'], r['MapId'], r['Scale'], r['Offset']['X'], r['Offset']['Y'], r['Offset']['Z'])
        cursor.execute(ins,data)
    except KeyError:
        pass
    
conn.commit()

cursor.execute("DELETE FROM 'hunts'")

ins=("INSERT INTO 'hunts' ('id','name','rank','expansion','spawn_min','spawn_max') VALUES (?, ?, ?, ?, ?, ?)")        
for r in hunt.values():
    data=(r['Id'],r['Name']['English'], r['Rank'], r['Expansion'], r['SpawnTimers']['Normal']['Minimum'], r['SpawnTimers']['Normal']['Maximum'])
    cursor.execute(ins,data)
    
conn.commit()