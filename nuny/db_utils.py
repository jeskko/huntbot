import sqlite3,datetime

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
        r=[("Unknown",datetime.datetime(1899,12,30))]
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
    time=datetime.datetime.utcnow()-datetime.timedelta(days=7)
    cursor.execute(sel,(time,))
    return cursor.rowcount