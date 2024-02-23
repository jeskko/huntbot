import yaml
import nuny.config

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
    for i in nuny.config.conf["worlds"]:
        channels[i[5]["channel"]]=0
        channels[i[6]["channel"]]=0
    state["statuses"]=channels
    print(state)
    savestate()
