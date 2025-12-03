# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# (c) IT4Innovations, VSB-TUO

import functools
import logging
import typing

import signal
import sys
import asyncio
#import aiohttp
import json
import requests
import bpy

log = logging.getLogger(__name__)

#@functools.lru_cache(maxsize=None)
def get_endpoint(endpoint_path=None):
    """Gets the endpoint for the authentication API. If the BHRAAS_SERVER_ENDPOINT env variable
    is defined, it's possible to override the (default) production address.
    """
    #import os
    from . import raas_pref
    from . import raas_config
    import urllib.parse
    import functools

    #base_url = raas_config.GetServer(raas_pref.preferences().raas_pid.lower())
    #pid_name, pid_queue, pid_dir = raas_config.GetCurrentPidInfo(bpy.context, raas_pref.preferences())
    pid_name, pid_queue, pid_dir = bpy.context.scene.raas_config_functions.call_get_current_pid_info(bpy.context, raas_pref.preferences())
    base_url = raas_config.GetServer(pid_name.lower())

    # urljoin() is None-safe for the 2nd parameter.
    return urllib.parse.urljoin(base_url, endpoint_path)


async def post_json(endpoint, data_json):
    url = get_endpoint(endpoint)

    print('Sending request to: %s' % url)
    raas_client = requests.session()
    response = raas_client.request('POST', url, data = data_json, headers={'Content-Type': 'application/json'})    

    if 200 > response.status_code or 299 < response.status_code:
        raise Exception('Http post error: text: %s, status: %d, url: %s' % (response.text, response.status_code, url))

    return response.text

async def post(endpoint, data):
    #import json
    
    data_json = json_dumps(data)  
    resp = await post_json(endpoint, data_json)
    try:
        resp_json = json.loads(resp) #.decode('utf-8')
    except json.JSONDecodeError:
        raise Exception('JSONDecodeError: {}'.format(resp)) #.decode('utf-8')

    return resp_json

async def get_token(username: str, password: str) -> str:

    data = {
        "Credentials" : {
            "Username" : username,
            "Password" : password,
        }
    }

    if username is None or len(username) < 1 or password is None or len(password) < 1:
        raise Exception('username or password is empty')

    #import json
    data_json = json_dumps(data)
    resp = await post_json("UserAndLimitationManagement/AuthenticateUserPassword", data_json)
    
    if resp is None or len(resp) != 38:
        raise Exception('username or password is wrong')

    
    return resp.replace('"','') #.decode('utf-8')     

local_to_server_map = {
    "Id" : "Id",
    "Name" : "Name",
    "State" : "State",
    "Priority" : "Priority",
    "Project" : "Project",
    "CreationTime" : "CreationTime",
    "SubmitTime" : "SubmitTime",
    "StartTime" : "StartTime",
    "EndTime" : "EndTime",
    "TotalAllocatedTime" : "TotalAllocatedTime",
    "AllParameters" : "AllParameters",
    "Tasks": "Tasks",

    "Credentials": "Credentials",
    "PrivateKey": "PrivateKey",
    "ServerHostname": "ServerHostname",
    "SharedBasepath": "SharedBasepath",
    "UserName":  "Username"
}

def fill_items(dest, src):
    for item in dest.__dir__():
        if item in src:
            dest[item] = src[item]
        elif item in local_to_server_map and local_to_server_map[item] in src:
            dest[item] = src[local_to_server_map[item]]
        else:
            dest[item] = None

def json_dumps(data):
    return json.dumps(data, separators=(',', ':'))
