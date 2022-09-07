import logging
import random
import string
import requests
import subprocess
import socket
import time

import telegram.ext as tg

from os import path, remove, getenv
from dotenv import load_dotenv
from telegraph import Telegraph
from telegraph.exceptions import RetryAfterError
from threading import Lock

socket.setdefaulttimeout(600)

botStartTime = time.time()

if path.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
                    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

CONFIG_ENV_URL = getenv('CONFIG_ENV_URL')
try:
    if not CONFIG_ENV_URL:
        raise ValueError("CONFIG_ENV_URL Not Found !")
    res = requests.get(CONFIG_ENV_URL)
    if res.status_code == 200:
        with open('config.env', 'wb+') as f:
            f.write(res.content)
    else:
        LOGGER.error(f"Failed to load config.env file [{res.status_code}]")
except Exception as e:
    LOGGER.error(f"CONFIG_ENV_URL: {e}")

load_dotenv('config.env', override=True)

Interval, TELEGRAPH = [], []
DRIVE_NAMES, DRIVE_IDS, INDEX_URLS = [], [], []

AUTHORIZED_CHATS = set()

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}

BOT_TOKEN = getenv('BOT_TOKEN')
if not BOT_TOKEN:
    LOGGER.error("BOT_TOKEN env variable is missing")
    exit(1)

OWNER_ID = getenv('OWNER_ID')
if not OWNER_ID:
    LOGGER.error("OWNER_ID env variable is missing")
    exit(1)
OWNER_ID = int(OWNER_ID)

PARENT_ID = getenv('DRIVE_FOLDER_ID')
if not PARENT_ID:
    LOGGER.error("DRIVE_FOLDER_ID env variable is missing")
    exit(1)

DOWNLOAD_DIR = getenv('DOWNLOAD_DIR')
if not DOWNLOAD_DIR:
    LOGGER.error("DOWNLOAD_DIR env variable is missing")
    exit(1)
if not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR = DOWNLOAD_DIR + '/'

users = getenv('AUTHORIZED_CHATS')
if users:
    AUTHORIZED_CHATS.update([int(user.strip()) for user in users.split()])

DATABASE_URL = getenv('DATABASE_URL')

IS_TEAM_DRIVE = str(getenv('IS_TEAM_DRIVE', False)).lower() == "true"

USE_SERVICE_ACCOUNTS = str(getenv('USE_SERVICE_ACCOUNTS', False)).lower() == 'true'

STATUS_UPDATE_INTERVAL = int(getenv('STATUS_UPDATE_INTERVAL', 10))

TELEGRAPH_ACCS = int(getenv('TELEGRAPH_ACCS', 1))

INDEX_URL = str(getenv('INDEX_URL')).rstrip("/")

CLONE_LIMIT = getenv('CLONE_LIMIT')
if CLONE_LIMIT:
    CLONE_LIMIT = float(CLONE_LIMIT)

COMPRESS_LIMIT = getenv('COMPRESS_LIMIT')
if COMPRESS_LIMIT:
    COMPRESS_LIMIT = float(COMPRESS_LIMIT)

TOKEN_JSON_URL = getenv('TOKEN_JSON_URL')
try:
    if not TOKEN_JSON_URL:
        raise ValueError("TOKEN_JSON_URL Not Found !")
    res = requests.get(TOKEN_JSON_URL)
    if res.status_code == 200:
        with open('token.json', 'wb+') as f:
            f.write(res.content)
    else:
        LOGGER.error(f"Failed to load token.json file [{res.status_code}]")
except Exception as e:
    LOGGER.error(f"TOKEN_JSON_URL: {e}")

ACCOUNTS_ZIP_URL = getenv('ACCOUNTS_ZIP_URL')
try:
    if not ACCOUNTS_ZIP_URL:
        raise ValueError("ACCOUNTS_ZIP_URL Not Found !")
    res = requests.get(ACCOUNTS_ZIP_URL)
    if res.status_code == 200:
        with open('accounts.zip', 'wb+') as f:
            f.write(res.content)
    else:
        LOGGER.error(f"Failed to load accounts.zip file [{res.status_code}]")
    
    if path.exists("accounts.zip"):
        subprocess.run(["unzip", "-q", "-o", "accounts.zip"])
        subprocess.run(["chmod", "-R", "777", "accounts"])
        remove("accounts.zip")
except Exception as e:
    LOGGER.error(f"ACCOUNTS_ZIP_URL: {e}")

DRIVE_LIST_URL = getenv('DRIVE_LIST_URL')
try:
    if not DRIVE_LIST_URL:
        raise ValueError("DRIVE_LIST_URL Not Found !")
    res = requests.get(DRIVE_LIST_URL)
    if res.status_code == 200:
        with open('drive_list', 'wb+') as f:
            f.write(res.content)
    else:
        LOGGER.error(f"Failed to load drive_list file [{res.status_code}]")
except Exception as e:
    LOGGER.error(f"DRIVE_LIST_URL: {e}")

APPDRIVE_EMAIL, APPDRIVE_PASS = getenv('APPDRIVE_EMAIL'), getenv('APPDRIVE_PASS')

GDTOT_CRYPT = getenv('GDTOT_CRYPT')

if path.exists('drive_list'):
    with open('drive_list', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            try:
                temp = line.strip().split()
                DRIVE_NAMES.append(temp[0].replace("_", " ")), DRIVE_IDS.append(temp[1])
            except:
                pass
            try:
                INDEX_URLS.append(temp[2])
            except IndexError:
                INDEX_URLS.append(None)

def create_account(sname):
    try:
        telegra_ph = Telegraph()
        telegra_ph.create_account(short_name=sname)
        telegraph_token = telegra_ph.get_access_token()
        TELEGRAPH.append(Telegraph(access_token=telegraph_token))
        time.sleep(0.5)
    except RetryAfterError as e:
        LOGGER.info(f"Cooldown: {e.retry_after} seconds")
        time.sleep(e.retry_after)
        create_account(sname)

for _ in range(TELEGRAPH_ACCS):
    sname = ''.join(random.SystemRandom().choices(string.ascii_letters, k=8))
    create_account(sname)
LOGGER.info(f"Generated {TELEGRAPH_ACCS} telegraph tokens")

updater = tg.Updater(token=BOT_TOKEN, use_context=True)
bot = updater.bot
dispatcher = updater.dispatcher
