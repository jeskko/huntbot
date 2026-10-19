import sqlite3,datetime

def adapt_datetime_utc(val: datetime.datetime) -> str:
    if val.tzinfo is None:
    
        val = val.replace(tzinfo=datetime.timezone.utc)
    else:
        val = val.astimezone(datetime.timezone.utc)
    return val.isoformat()

def convert_timestamp_utc(val: bytes) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(val.decode())
    if dt.tzinfo is None:
        # Existing naive data in the DB → treat as UTC
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


sqlite3.register_adapter(datetime.datetime, adapt_datetime_utc)
sqlite3.register_converter("timestamp", convert_timestamp_utc)
sqlite3.register_converter("datetime", convert_timestamp_utc)

try:
    conn
except NameError:
    conn = sqlite3.connect('hunt.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cursor=conn.cursor()

def getworldid(world):
    sel="""
    SELECT id FROM 'worlds'
    WHERE name=?
    """
    cursor.execute(sel,(world,))
    r=cursor.fetchall()[0][0]
    return(r)

def getstatus(world,exp):
    sel="""
    SELECT status,time from 'status'
    WHERE worldid=? AND expansion=? ORDER BY time DESC LIMIT 1
    """
    worldid=getworldid(world)
    cursor.execute(sel,(worldid,exp))
    r=cursor.fetchall()
    if len(r)==0:
        r=[("Unknown",datetime.datetime(1899,12,30, tzinfo=datetime.timezone.utc))]
    return ((r[0][0],r[0][1]))

def setstatus(world,exp,status,time):
    ins="""
    INSERT INTO 'status' 
    (worldid,expansion,status,time)
    VALUES(?,?,?,?)
    """
    
    worldid=getworldid(world)
    cursor.execute(ins,(worldid,exp,status,time))
    return

def unscout(world,exp):
    sel="""
    SELECT time from 'status'
    WHERE worldid=? AND expansion=? AND status!="Scouted" AND status!="Scouting" ORDER BY time DESC LIMIT 1
    """
    worldid=getworldid(world)
    cursor.execute(sel,(worldid,exp))
    r=cursor.fetchall()
    if len(r)==0:
        raise ValueError
    time=r[0][0]
    sel="""
    DELETE from 'status'
    WHERE worldid=? AND expansion=? AND (status="Scouted" OR status="Scouting") and TIME>?
    """
    cursor.execute(sel,(worldid,exp,time))
    return cursor.rowcount

def gethistory(world,exp,time=None):
    sel="""
    SELECT id,status,time from 'status'
    WHERE worldid=? and expansion=? ORDER BY time DESC LIMIT 10
    """
    worldid=getworldid(world)
    cursor.execute(sel,(worldid,exp))
    r=cursor.fetchall()
    return r

def delstatus(id):
    sel="""
    DELETE from 'status'
    WHERE id=?
    """
    id=int(id)
    cursor.execute(sel,(id,))
    return

def settime(id,time):
    sel="""
    UPDATE 'status'
    SET time=?
    WHERE id=?
    """
    id=int(id)
    cursor.execute(sel,(time,id))

def cleanup():
    sel="""
    DELETE from 'status'
    WHERE time<?
    """
    time=datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=7)
    cursor.execute(sel,(time,))
    return cursor.rowcount