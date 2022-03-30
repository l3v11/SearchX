import logging
import os
import random
import string
import requests
import subprocess
import socket
import time

import telegram.ext as tg

from dotenv import load_dotenv
from telegraph import Telegraph

socket.setdefaulttimeout(600)

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

if os.path.exists('authorized_chats.txt'):
    with open('authorized_chats.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            AUTHORIZED_CHATS.add(int(line.split()[0]))

try:
    users = get_config('AUTHORIZED_CHATS')
    users = users.split(" ")
    for user in users:
        AUTHORIZED_CHATS.add(int(user))
except:
    pass

try:
    TOKEN_JSON_URL = get_config('TOKEN_JSON_URL')
    if len(TOKEN_JSON_URL) == 0:
        TOKEN_JSON_URL = None
    else:
        res = requests.get(TOKEN_JSON_URL)
        if res.status_code == 200:
            with open('token.json', 'wb+') as f:
                f.write(res.content)
                f.close()
        else:
            LOGGER.error(f"Failed to load token.json file [{res.status_code}]")
            raise KeyError
except KeyError:
    pass

try:
    BOT_TOKEN = get_config('BOT_TOKEN')
    OWNER_ID = int(get_config('OWNER_ID'))
    parent_id = get_config('DRIVE_FOLDER_ID')
    TELEGRAPH_ACCS = None
    try:
        TELEGRAPH_ACCS = int(get_config('TELEGRAPH_ACCS'))
    except ValueError:
        TELEGRAPH_ACCS = 2
except KeyError:
    LOGGER.error("One or more env variables are missing")
    exit(1)

if not os.path.exists('token.json'):
    LOGGER.error("token.json file is missing")
    exit(1)

try:
    DATABASE_URL = get_config('DATABASE_URL')
    if len(DATABASE_URL) == 0:
        raise KeyError
except KeyError:
    DATABASE_URL = None

try:
    IS_TEAM_DRIVE = get_config('IS_TEAM_DRIVE')
    if IS_TEAM_DRIVE.lower() == 'true':
        IS_TEAM_DRIVE = True
    else:
        IS_TEAM_DRIVE = False
except KeyError:
    IS_TEAM_DRIVE = False

try:
    USE_SERVICE_ACCOUNTS = get_config('USE_SERVICE_ACCOUNTS')
    if USE_SERVICE_ACCOUNTS.lower() == 'true':
        USE_SERVICE_ACCOUNTS = True
    else:
        USE_SERVICE_ACCOUNTS = False
except KeyError:
    USE_SERVICE_ACCOUNTS = False

try:
    APPDRIVE_EMAIL = get_config('APPDRIVE_EMAIL')
    APPDRIVE_PASS = get_config('APPDRIVE_PASS')
    if len(APPDRIVE_EMAIL) == 0 or len(APPDRIVE_PASS) == 0:
        raise KeyError
except KeyError:
    APPDRIVE_EMAIL = None
    APPDRIVE_PASS = None

try:
    GDTOT_CRYPT = get_config('GDTOT_CRYPT')
    if len(GDTOT_CRYPT) == 0:
        raise KeyError
except KeyError:
    GDTOT_CRYPT = None

try:
    DRIVE_INDEX_URL = get_config('DRIVE_INDEX_URL')
    if len(DRIVE_INDEX_URL) == 0:
        DRIVE_INDEX_URL = None
except KeyError:
    DRIVE_INDEX_URL = None

try:
    ACCOUNTS_ZIP_URL = get_config('ACCOUNTS_ZIP_URL')
    if len(ACCOUNTS_ZIP_URL) == 0:
        ACCOUNTS_ZIP_URL = None
    else:
        res = requests.get(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open('accounts.zip', 'wb+') as f:
                f.write(res.content)
                f.close()
        else:
            LOGGER.error(f"Failed to load accounts.zip file [{res.status_code}]")
            raise KeyError
        subprocess.run(["unzip", "-q", "-o", "accounts.zip"])
        subprocess.run(["chmod", "-R", "777", "accounts"])
        os.remove("accounts.zip")
except KeyError:
    pass

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

telegraph = []

for i in range(TELEGRAPH_ACCS):
    sname = ''.join(random.SystemRandom().choices(string.ascii_letters, k=8))
    telegra_ph = Telegraph()
    telegra_ph.create_account(short_name=sname)
    telegraph_token = telegra_ph.get_access_token()
    telegraph.append(Telegraph(access_token=telegraph_token))
    time.sleep(0.5)
LOGGER.info(f"Generated {TELEGRAPH_ACCS} telegraph tokens")

updater = tg.Updater(token=BOT_TOKEN, use_context=True)
bot = updater.bot
dispatcher = updater.dispatcher
