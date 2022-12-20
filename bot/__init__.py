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
from telegraph.exceptions import RetryAfterError
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

CONFIG_ENV_URL = os.environ.get('CONFIG_ENV_URL', '')
if len(CONFIG_ENV_URL) != 0:
    try:
        res = requests.get(CONFIG_ENV_URL)
        if res.status_code == 200:
            with open('config.env', 'wb+') as f:
                f.write(res.content)
        else:
            LOGGER.error(f"Failed to load the config.env file [{res.status_code}]")
    except Exception as err:
        LOGGER.error(f"CONFIG_ENV_URL: {err}")

load_dotenv('config.env', override=True)

Interval = []
DRIVE_NAMES = []
DRIVE_IDS = []
INDEX_URLS = []
TELEGRAPH = []
BOOKMARKS = {}

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    LOGGER.error("BOT_TOKEN env variable is missing")
    exit(1)

OWNER_ID = os.environ.get('OWNER_ID', '')
if len(OWNER_ID) == 0:
    LOGGER.error("OWNER_ID env variable is missing")
    exit(1)
else:
    OWNER_ID = int(OWNER_ID)

DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '')
if len(DRIVE_FOLDER_ID) == 0:
    LOGGER.error("DRIVE_FOLDER_ID env variable is missing")
    exit(1)

users = os.environ.get('AUTHORIZED_USERS', '')
if len(users) != 0:
    AUTHORIZED_USERS = {int(user.strip()) for user in users.split()}
else:
    AUTHORIZED_USERS = set()

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if len(DATABASE_URL) == 0:
    DATABASE_URL = None

IS_TEAM_DRIVE = os.environ.get('IS_TEAM_DRIVE', '')
IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'

USE_SERVICE_ACCOUNTS = os.environ.get('USE_SERVICE_ACCOUNTS', '')
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'

DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '')
if len(DOWNLOAD_DIR) == 0:
    DOWNLOAD_DIR = '/usr/src/app/downloads/'
elif not DOWNLOAD_DIR.endswith('/'):
    DOWNLOAD_DIR = f'{DOWNLOAD_DIR}/'

STATUS_UPDATE_INTERVAL = os.environ.get('STATUS_UPDATE_INTERVAL', '')
STATUS_UPDATE_INTERVAL = 10 if len(STATUS_UPDATE_INTERVAL) == 0 else int(STATUS_UPDATE_INTERVAL)

TELEGRAPH_ACCS = os.environ.get('TELEGRAPH_ACCS', '')
TELEGRAPH_ACCS = 1 if len(TELEGRAPH_ACCS) == 0 else int(TELEGRAPH_ACCS)

INDEX_URL = os.environ.get('INDEX_URL', '').rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = None

ARCHIVE_LIMIT = os.environ.get('ARCHIVE_LIMIT', '')
ARCHIVE_LIMIT = None if len(ARCHIVE_LIMIT) == 0 else float(ARCHIVE_LIMIT)

CLONE_LIMIT = os.environ.get('CLONE_LIMIT', '')
CLONE_LIMIT = None if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

TOKEN_JSON_URL = os.environ.get('TOKEN_JSON_URL', '')
if len(TOKEN_JSON_URL) != 0:
    try:
        res = requests.get(TOKEN_JSON_URL)
        if res.status_code == 200:
            with open('token.json', 'wb+') as f:
                f.write(res.content)
        else:
            LOGGER.error(f"Failed to load the token.json file [{res.status_code}]")
    except Exception as err:
        LOGGER.error(f"TOKEN_JSON_URL: {err}")

ACCOUNTS_ZIP_URL = os.environ.get('ACCOUNTS_ZIP_URL', '')
if len(ACCOUNTS_ZIP_URL) != 0:
    try:
        res = requests.get(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open('accounts.zip', 'wb+') as f:
                f.write(res.content)
            subprocess.run(["unzip", "-q", "-o", "accounts.zip", "-x", "accounts/emails.txt"])
            subprocess.run(["chmod", "-R", "777", "accounts"])
            os.remove("accounts.zip")
        else:
            LOGGER.error(f"Failed to load the accounts.zip file [{res.status_code}]")
    except Exception as err:
        LOGGER.error(f"ACCOUNTS_ZIP_URL: {err}")

DRIVE_LIST_URL = os.environ.get('DRIVE_LIST_URL', '')
if len(DRIVE_LIST_URL) != 0:
    try:
        res = requests.get(DRIVE_LIST_URL)
        if res.status_code == 200:
            with open('drive_list', 'wb+') as f:
                f.write(res.content)
        else:
            LOGGER.error(f"Failed to load the drive_list file [{res.status_code}]")
    except Exception as err:
        LOGGER.error(f"DRIVE_LIST_URL: {err}")

GDTOT_CRYPT = os.environ.get('GDTOT_CRYPT', '')
if len(GDTOT_CRYPT) == 0:
    GDTOT_CRYPT = None

if os.path.exists('drive_list'):
    with open('drive_list', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            DRIVE_NAMES.append(temp[0].replace("_", " "))
            DRIVE_IDS.append(temp[1])
            if len(temp) > 2:
                INDEX_URLS.append(temp[2])
            else:
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

for i in range(TELEGRAPH_ACCS):
    sname = ''.join(random.SystemRandom().choices(string.ascii_letters, k=8))
    create_account(sname)
LOGGER.info(f"Generated {TELEGRAPH_ACCS} telegraph tokens")

tgDefaults = tg.Defaults(parse_mode='HTML', allow_sending_without_reply=True, disable_web_page_preview=True, run_async=True)
updater = tg.Updater(token=BOT_TOKEN, defaults=tgDefaults, use_context=True)
bot = updater.bot
dispatcher = updater.dispatcher
