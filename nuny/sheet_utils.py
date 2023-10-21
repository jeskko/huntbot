import os,datetime
import logging
from tabulate import tabulate
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google.oauth2 import service_account

import nuny.config

def worldTimeLoc(world,leg=None):
    """
    Find the sheet cell location for time value for a certain world.
    leg==1 means SHB, otherwise EW.
    """
    
    if leg==1:
        l=5
    else:
        l=6
    try: 
        w=[w for w in nuny.config.conf["worlds"] if w["name"]==world][0]
    except IndexError:
        raise ValueError("Invalid world")
    return w[l]["time"]

def worldStatusLoc(world,leg=None):
    """
    Find the sheet cell location for status value for a certain world.
    leg==1 means SHB, otherwise EW.    
    """
    
    if leg==1:
        l=5
    else:
        l=6
    try: 
        w=[w for w in nuny.config.conf["worlds"] if w["name"]==world][0]
    except IndexError:
        raise ValueError("Invalid world")
    return w[l]["status"]

async def update_sheet(world, status, time, legacy=None):
    """Update the backend sheet."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    creds = None

    secret=os.path.join(os.getcwd(),'nuny.json')
    creds = service_account.Credentials.from_service_account_file(secret,scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)

    sheet=service.spreadsheets()
    timecell="Up Times!"+worldTimeLoc(world,legacy)
    statuscell="Up Times!"+worldStatusLoc(world,legacy)
    if time != 0:
        temp=datetime.datetime(1899,12,30)
        delta=time-temp
        time=float(delta.days)+(float(delta.seconds)/86440)
        body={
                "valueInputOption": "RAW",
                "data": [
                    {
                        'range': timecell,
                        'values': [[time]]
                    },
                    {
                        'range': statuscell,
                        'values': [[status]]
                    }
                ]
            }

    else:
        body={
                "valueInputOption": "RAW",
                "data": [
                    {
                        'range': statuscell,
                        'values': [[status]]
                    }
                ]
            }

    response=sheet.values().batchUpdate(spreadsheetId=nuny.config.conf["google"]["spreadsheet"], body=body).execute()

def fetch_sheet(range):
    """Fetch data from the backend sheet."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    secret=os.path.join(os.getcwd(),'nuny.json')
    creds = service_account.Credentials.from_service_account_file(secret,scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet=service.spreadsheets()
    try:
        result=sheet.values().get(spreadsheetId=nuny.config.conf["google"]["spreadsheet"], range=range, valueRenderOption="UNFORMATTED_VALUE").execute()
    except HttpError as err:
        logging.error(f"HttpError on fetch_sheet {err.resp.status}")
        return 0
    return result.get('values', [])

async def update_from_sheets():
    """Fetch data from backend sheet and update channel names."""
    
    EW_RANGE = 'Up Times!B3:E10'
    LEGACY_RANGE = 'Up Times!B20:E27'

    values=fetch_sheet(EW_RANGE)

    if not values:
        logging.error('No data found from fetch_sheet.')
    else:
        for row in values:
            await update_channel(row[0],row[3],0)

    values=fetch_sheet(LEGACY_RANGE)

    if not values:
        logging.error('No data found from fetch_sheet.')
    else:
        for row in values:
            await update_channel(row[0],row[3],1)

async def update_from_sheets_to_chat(legacy=None):
    """Fetch status from backend sheet and make a status summary."""
    
    range = 'Up Times!B3:E10'
    message="Endwalker status\n```"
    if legacy==1:
        range = 'Up Times!B20:E27'
        message="Shadowbringers status\n```"
    
    values=fetch_sheet(range)

    if not values:
        logging.error('No data found from fetch_sheet.')
    else:
        taulu=[]
        taulu.append(["Server","Status\nchanged","+6h","Status\nduration","Status"])
        for row in values:
            t1=datetime.datetime.strftime(datetime.datetime(1899,12,30)+datetime.timedelta(days=row[1]),"%d.%m %H:%M")
            if row[3]=="Dead":
                t2=datetime.datetime.strftime(datetime.datetime(1899,12,30)+datetime.timedelta(days=row[2]),"%H:%M")
            else:
                t2=""
            t3_td=datetime.datetime.utcnow()-(datetime.datetime(1899,12,30)+datetime.timedelta(days=row[1]))
            t3_h=int(divmod(t3_td.total_seconds(),3600)[0])
            t3_m=int(divmod(divmod(t3_td.total_seconds(),3600)[1],60)[0])
            if t3_h<0:
                t3=""
            else:
                t3=f"{t3_h}:{t3_m:02d}"
            
            taulu.append([row[0],t1,t2,t3,row[3]])
        message+=tabulate(taulu,headers="firstrow",tablefmt="fancy_grid")+"```"
    return message

async def update_from_sheets_to_compact_chat(legacy=None):
    """Fetch status from backend sheet and make a compact status summary suitable for eg. mobile use."""
    
    range = 'Up Times!B33:D40'
    values=fetch_sheet(range)
    
    if not values:
        logging.error('No data found from fetch_sheet.')
    else:
        taulu=[]
        taulu.append(["Server","EW","SHB"])
        for row in values:
            taulu.append([row[0],row[1],row[2]])
    message="```"+tabulate(taulu,headers="firstrow",tablefmt="fancy_grid")+"```"
    return message

async def update_channel(world, status, legacy=None):
    """Update channel name value. Will check if actual update is necessary to avoid rate limiting."""
    
    if legacy==1:
        l=5
    else:
        l=6
    try:
        w=[w for w in nuny.config.conf["worlds"] if w["name"]==world][0]
    except IndexError:
        raise ValueError("Invalid world")
    try:
        st=[st for st in nuny.config.conf["statuses"] if st["name"]==status][0]
    except IndexError:
        raise ValueError("Invalid world status")
    chanid=w[l]["channel"]
    newname=f'{st["icon"]}{w["short"]}-{st["short"]}'
     
    chan=nuny.discord_utils.bot.get_channel(chanid)
    if chan.name != newname:
        logging.debug(f"Updating channel name from {chan.name} to {newname}.")
        await chan.edit(name=newname)
    else:
        logging.debug("no need to update channel name.")