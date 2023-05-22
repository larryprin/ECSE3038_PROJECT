from fastapi import FastAPI,HTTPException,Request
from bson import ObjectId
import motor.motor_asyncio
from fastapi.middleware.cors import CORSMiddleware
import pydantic
import os
from dotenv import load_dotenv
from datetime import datetime,timedelta
import uvicorn
import json
import requests
import pytz
import re

referencetemp=28.0

app = FastAPI()



load_dotenv() 
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_DB_URL'))
db = client.stuff.date


pydantic.json.ENCODERS_BY_TYPE[ObjectId]=str

origins = ["https://simple-smart-hub-client.netlify.app",
           "http://localhost:8000",
           ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sunset():
    sunset_response=requests.get(f'https://api.sunrise-sunset.org/json?lat=18.1096&lng=-77.2975&date=today')
    sunset_json = sunset_response.json()
    sunset_time_date = sunset_json["results"]["sunset"] #Returns Sunset in UTC Time
    sunset_time_date = datetime.strptime(sunset_time_date,'%I:%M:%S %p') + timedelta(hours=-5) #Converting form UTC to GMT-5 (Our Timezone)
    sunset_time_date = datetime.strftime(sunset_time_date,'%H:%M:%S') 
    return sunset_time_date

regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)


@app.post("/api/state",status_code=201) 
async def set_state(request:Request):
    
    state = await request.json()
    state["datetime"]=(datetime.now()+timedelta(hours=-5)).strftime('%Y-%m-%dT%H:%M:%S')
    new_state = await db["states"].insert_one(state)
    updated_state = await db["states"].find_one({"_id": new_state.inserted_id }) 
    if new_state.acknowledged == True:
        return updated_state
    raise HTTPException(status_code=400,detail="Issue")

#GET /data
@app.get("/api/state")
async def getstate():
    current_state = await db["states"].find().sort("datetime",-1).to_list(1)
    current_settings = await db["settings"].find().to_list(1)
    presence = current_state[0]["presence"]
    
    time_now=datetime.strptime(datetime.strftime(datetime.now()+timedelta(hours=-5),'%Y-%m-%dT%H:%M:%S'),'%Y-%m-%dT%H:%M:%S')
    user_light=datetime.strptime(current_settings[0]["user_light"],'%Y-%m-%dT%H:%M:%S')
    lightoff=datetime.strptime(current_settings[0]["light_time_off"],'%Y-%m-%dT%H:%M:%S')

    fan_state = ((float(current_state[0]["temperature"])>float(current_settings[0]["user_temp"])) and presence)  #Watch Formatting here
    light_state = (time_now>user_light) and (presence) and (time_now<lightoff)
    
    
    print(datetime.strftime(datetime.now()+timedelta(hours=-5),'%Y-%m-%dT%H:%M:%S'))
    print(current_settings[0]["user_light"])
    print(current_settings[0]["light_time_off"])
    print(presence)

    fan_of_light ={"fan":fan_state, "light":light_state}
    return fan_of_light


#GET /Graph
@app.get("/graph", status_code=200)
async def graphpoints(request:Request,size: int):
    n = size
    statearray = await db["states"].find().sort("datetime",-1).to_list(n)
    statearray.reverse()
    return statearray


#PUT /Settings
@app.put("/settings",status_code=200)
async def setting(request:Request):
    
    setting = await request.json()
    elements = await db["settings"].find().to_list(1)
    mod_setting = {}
    mod_setting["user_temp"]=setting["user_temp"]
    if setting["user_light"]== "sunset":
        timestring = sunset()
    else:
        timestring = setting["user_light"]

    mod_setting["user_light"]=(datetime.now().date()).strftime("%Y-%m-%dT")+timestring
    mod_setting["light_time_off"]= ((datetime.strptime(mod_setting["user_light"],'%Y-%m-%dT%H:%M:%S')+parse_time(setting["light_duration"])).strftime('%Y-%m-%dT%H:%M:%S'))
    print(mod_setting["user_light"])
    print(mod_setting["light_time_off"])
    

    if len(elements)==0:
         new_setting = await db["settings"].insert_one(mod_setting)
         patched_setting = await db["settings"].find_one({"_id": new_setting.inserted_id }) 
         return patched_setting
    else:
        id=elements[0]["_id"]
        updated_setting= await db["settings"].update_one({"_id":id},{"$set": mod_setting})
        patched_setting = await db["settings"].find_one({"_id": id}) 
        if updated_setting.modified_count>=1: 
            return patched_setting
    raise HTTPException(status_code=400,detail="Issue")