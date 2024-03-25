#!/usr/bin/python3

# Import OS functions
import os

# Import dependencies web server
import datetime
import asyncio
from database import getData
from utils import *
from printer import *
import global_vars


# Setup
def setup():
    try:
        log('Print server is starting...')
        if is_online():
            log('Network connection found.')
            ip = get_local_ip()
            log(f'Manage your printer at {ip}.')
        else:
            log('No network connection found.', 'error')
    except Exception as e:
        log(e, 'error')
        raise e


async def print_loop(user:str, db):
    try:
        data = await getData(db, user);
        log(f'Received {len(data)} new messages! Press the print button or unlock in the print queue.')
        
        combinded_list = data + global_vars.messages
        global_vars.messages = combinded_list
        # log(f'Message list: {global_vars.messages}.')
        
    except Exception as e:
        log(e, 'error')
        raise e

async def unlock_and_print_mssg(messageId, user, db):
    print('unlocking...')
    try:
        received_time = datetime.datetime.now();
        new_message_list = []
        for message in global_vars.messages:
            targetId = list(message.keys())[0]
            if targetId == messageId:
                modified_message = message[messageId]
                modified_message['printed'] = received_time
                new_message_list.append({
                    targetId: modified_message
                })
            else:
                new_message_list.append(message)
        global_vars.messages = new_message_list
        
        return True
    except Exception as e:
        log(e, 'error')
        raise e



