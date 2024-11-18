import yaml
import nuny.config

"""
For tracking server status messages on status channels
"""

def savestate():
    with open('state.yaml', "w") as file:
        yaml.dump(state,file,default_flow_style=False)
        
try:
    state
except NameError:
    try:
        with open('state.yaml', 'r') as file:
            state = yaml.safe_load(file)
    except FileNotFoundError:
        state=""
    
if type(state) is not dict:
    state={}
    channels={}
    for i in nuny.config.conf["channels"]["worlds"]:
        channels[i["channels"][5]]=0
        channels[i["channels"][6]]=0
        channels[i["channels"][7]]=0
    state["statuses"]=channels
    savestate()
