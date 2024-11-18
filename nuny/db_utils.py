import sqlite3,datetime

try:
    conn
except NameError:
    conn = sqlite3.connect('hunt.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cursor=conn.cursor()

def getstatus(world,exp):
    return ("Up", datetime.datetime.utcnow())

def setstatus(world,exp,status,time):
    return

def settimer(world,ex,time):
    return

