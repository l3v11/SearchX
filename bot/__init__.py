import logging
import os
import time
import random
import string
import requests

import telegram.ext as tg

from dotenv import load_dotenv
from telegraph import Telegraph

if os.path.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
                    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

def get_config(name: str):
    return os.environ[name]

try:
    CONFIG_ENV_URL = get_config('CONFIG_ENV_URL')
    if len(CONFIG_ENV_URL) == 0:
        CONFIG_ENV_URL = None
    else:
        res = requests.get(CONFIG_ENV_URL)
        if res.status_code == 200:
            with open('config.env', 'wb+') as f:
                f.write(res.content)
                f.close()
        else:
            LOGGER.error(f"Failed to load config.env file [{res.status_code}]")
            raise KeyError
except KeyError:
    pass

load_dotenv('config.env')

AUTHORIZED_CHATS = set()

try:
    auths = get_config('AUTHORIZED_CHATS')
    auths = auths.split(" ")
    for chats in auths:
        AUTHORIZED_CHATS.add(int(chats))
except:
    pass

try:
    BOT_TOKEN = get_config('BOT_TOKEN')
    OWNER_ID = int(get_config('OWNER_ID'))
except KeyError:
    LOGGER.error("One or more env variables are missing")
    exit(1)

try:
    if len(get_config('DRIVE_TOKEN')) == 0 or str(get_config('DRIVE_TOKEN')).lower() == "empty":
        LOGGER.error("DRIVE_TOKEN var is missing")
        exit(1)
    with open('token.json', 'wt') as f:
        f.write(get_config('DRIVE_TOKEN').replace("\n",""))
except:
    LOGGER.error("Failed to create token.json file")
    exit(1)

try:
    DRIVE_LIST_URL = get_config('DRIVE_LIST_URL')
    if len(DRIVE_LIST_URL) == 0:
        DRIVE_LIST_URL = None
    else:
        res = requests.get(DRIVE_LIST_URL)
        if res.status_code == 200:
            with open('drive_list', 'wb+') as f:
                f.write(res.content)
                f.close()
        else:
            LOGGER.error(f"Failed to load drive_list file [{res.status_code}]")
            raise KeyError
except KeyError:
    pass

DRIVE_NAME = []
DRIVE_ID = []
INDEX_URL = []

if os.path.exists('drive_list'):
    with open('drive_list', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            DRIVE_NAME.append(temp[0].replace("_", " "))
            DRIVE_ID.append(temp[1])
            try:
                INDEX_URL.append(temp[2])
            except IndexError:
                INDEX_URL.append(None)

if DRIVE_ID:
    pass
else:
    LOGGER.error("drive_list file is missing")
    exit(1)

# Generate Telegraph Token
sname = ''.join(random.SystemRandom().choices(string.ascii_letters, k=8))
LOGGER.info("Generating TELEGRAPH_TOKEN using '" + sname + "' name")
telegraph = Telegraph()
telegraph.create_account(short_name=sname)
telegraph_token = telegraph.get_access_token()
telegra_ph = Telegraph(access_token=telegraph_token)

updater = tg.Updater(token=BOT_TOKEN, use_context=True)
bot = updater.bot
dispatcher = updater.dispatcher
