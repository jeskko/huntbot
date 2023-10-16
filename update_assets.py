#!/usr/bin/env python3

import sqlite3,json,yaml 
from urllib.request import urlopen,Request

with open('config.yaml','r') as file:
    conf=yaml.safe_load(file)
    
assets=conf["sonar"]["asset"]

if conf["sonar"]["enable"]==False:
    exit()

conn = sqlite3.connect('hunt.db')
cursor=conn.cursor()

with urlopen(Request(assets["dc"], headers={'User-Agent': 'Nunyunuwi'})) as url:
     datacenter=json.load(url)
with urlopen(Request(assets["world"], headers={'User-Agent': 'Nunyunuwi'})) as url:
     world=json.load(url)
with urlopen(Request(assets["hunt"], headers={'User-Agent': 'Nunyunuwi'})) as url:
    hunt=json.load(url)
with urlopen(Request(assets["zone"], headers={'User-Agent': 'Nunyunuwi'})) as url:
    zone=json.load(url)
with urlopen(Request(assets["region"], headers={'User-Agent': 'Nunyunuwi'})) as url:
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