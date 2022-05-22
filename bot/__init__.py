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
from threading import Lock

socket.setdefaulttimeout(600)

botStartTime = time.time()

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
        raise KeyError
    try:
        res = requests.get(CONFIG_ENV_URL)
        if res.status_code == 200:
            with open('config.env', 'wb+') as f:
                f.write(res.content)
        else:
            LOGGER.error(f"Failed to load config.env file [{res.status_code}]")
    except Exception as e:
        LOGGER.error(f"CONFIG_ENV_URL: {e}")
except:
    pass

load_dotenv('config.env', override=True)

Interval = []
DRIVE_NAMES = []
DRIVE_IDS = []
INDEX_URLS = []
telegraph = []

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}

AUTHORIZED_CHATS = set()

try:
    users = get_config('AUTHORIZED_CHATS')
    users = users.split(" ")
    for user in users:
        AUTHORIZED_CHATS.add(int(user))
except:
    pass

try:
    BOT_TOKEN = get_config('BOT_TOKEN')
except:
    LOGGER.error("BOT_TOKEN env variable is missing")
    exit(1)

try:
    OWNER_ID = int(get_config('OWNER_ID'))
except:
    LOGGER.error("OWNER_ID env variable is missing")
    exit(1)

try:
    parent_id = get_config('DRIVE_FOLDER_ID')
except:
    LOGGER.error("DRIVE_FOLDER_ID env variable is missing")
    exit(1)

try:
    DATABASE_URL = get_config('DATABASE_URL')
    if len(DATABASE_URL) == 0:
        raise KeyError
except:
    DATABASE_URL = None

try:
    IS_TEAM_DRIVE = get_config('IS_TEAM_DRIVE')
    IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'
except:
    IS_TEAM_DRIVE = False

try:
    USE_SERVICE_ACCOUNTS = get_config('USE_SERVICE_ACCOUNTS')
    USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'
except:
    USE_SERVICE_ACCOUNTS = False

try:
    STATUS_UPDATE_INTERVAL = get_config('STATUS_UPDATE_INTERVAL')
    if len(STATUS_UPDATE_INTERVAL) == 0:
        raise KeyError
    STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)
except:
    STATUS_UPDATE_INTERVAL = 10

try:
    TELEGRAPH_ACCS = get_config('TELEGRAPH_ACCS')
    if len(TELEGRAPH_ACCS) == 0:
        raise KeyError
    TELEGRAPH_ACCS = int(TELEGRAPH_ACCS)
except:
    TELEGRAPH_ACCS = 1

try:
    INDEX_URL = get_config('INDEX_URL').rstrip("/")
    if len(INDEX_URL) == 0:
        raise KeyError
except:
    INDEX_URL = None

try:
    CLONE_LIMIT = get_config('CLONE_LIMIT')
    if len(CLONE_LIMIT) == 0:
        raise KeyError
    CLONE_LIMIT = float(CLONE_LIMIT)
except:
    CLONE_LIMIT = None

try:
    TOKEN_JSON_URL = get_config('TOKEN_JSON_URL')
    if len(TOKEN_JSON_URL) == 0:
        raise KeyError
    try:
        res = requests.get(TOKEN_JSON_URL)
        if res.status_code == 200:
            with open('token.json', 'wb+') as f:
                f.write(res.content)
        else:
            LOGGER.error(f"Failed to load token.json file [{res.status_code}]")
    except Exception as e:
        LOGGER.error(f"TOKEN_JSON_URL: {e}")
except:
    pass

try:
    ACCOUNTS_ZIP_URL = get_config('ACCOUNTS_ZIP_URL')
    if len(ACCOUNTS_ZIP_URL) == 0:
        raise KeyError
    try:
        res = requests.get(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open('accounts.zip', 'wb+') as f:
                f.write(res.content)
        else:
            LOGGER.error(f"Failed to load accounts.zip file [{res.status_code}]")
    except Exception as e:
        LOGGER.error(f"ACCOUNTS_ZIP_URL: {e}")
        raise KeyError
    subprocess.run(["unzip", "-q", "-o", "accounts.zip"])
    subprocess.run(["chmod", "-R", "777", "accounts"])
    os.remove("accounts.zip")
except:
    pass

try:
    DRIVE_LIST_URL = get_config('DRIVE_LIST_URL')
    if len(DRIVE_LIST_URL) == 0:
        raise KeyError
    try:
        res = requests.get(DRIVE_LIST_URL)
        if res.status_code == 200:
            with open('drive_list', 'wb+') as f:
                f.write(res.content)
        else:
            LOGGER.error(f"Failed to load drive_list file [{res.status_code}]")
    except Exception as e:
        LOGGER.error(f"DRIVE_LIST_URL: {e}")
except:
    pass

try:
    APPDRIVE_EMAIL = get_config('APPDRIVE_EMAIL')
    APPDRIVE_PASS = get_config('APPDRIVE_PASS')
    if len(APPDRIVE_EMAIL) == 0 or len(APPDRIVE_PASS) == 0:
        raise KeyError
except:
    APPDRIVE_EMAIL = None
    APPDRIVE_PASS = None

try:
    GDTOT_CRYPT = get_config('GDTOT_CRYPT')
    if len(GDTOT_CRYPT) == 0:
        raise KeyError
except:
    GDTOT_CRYPT = None

if os.path.exists('drive_list'):
    with open('drive_list', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            try:
                temp = line.strip().split()
                DRIVE_NAMES.append(temp[0].replace("_", " "))
                DRIVE_IDS.append(temp[1])
            except:
                pass
            try:
                INDEX_URLS.append(temp[2])
            except IndexError:
                INDEX_URLS.append(None)

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
