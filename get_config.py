from os import getenv, path
from dotenv import load_dotenv

if path.exists("config.env"):
    load_dotenv("config.env")

BOT_TOKEN= str(getenv('BOT_TOKEN'))
OWNER_ID= getenv('OWNER_ID')
DRIVE_FOLDER_ID= str(getenv('DRIVE_FOLDER_ID'))
DOWNLOAD_DIR= str(getenv('DOWNLOAD_DIR'))
AUTHORIZED_CHATS= str(getenv('AUTHORIZED_CHATS'))
DATABASE_URL= str(getenv('DATABASE_URL'))
IS_TEAM_DRIVE= getenv('IS_TEAM_DRIVE')
USE_SERVICE_ACCOUNTS= str(getenv('USE_SERVICE_ACCOUNTS'))
STATUS_UPDATE_INTERVAL= str(getenv('STATUS_UPDATE_INTERVAL'))
TELEGRAPH_ACCS= str(getenv('TELEGRAPH_ACCS'))
INDEX_URL= str(getenv('INDEX_URL'))
CLONE_LIMIT= getenv('CLONE_LIMIT')
COMPRESS_LIMIT= getenv('CLONE_LIMIT')
TOKEN_JSON_URL= str(getenv('TOKEN_JSON_URL'))
ACCOUNTS_ZIP_URL= str(getenv('ACCOUNTS_ZIP_URL'))
DRIVE_LIST_URL= str(getenv('DRIVE_LIST_URL'))
DEST_LIST_URL= str(getenv('DEST_LIST_URL'))
APPDRIVE_EMAIL= str(getenv('APPDRIVE_EMAIL'))
APPDRIVE_PASS= str(getenv('APPDRIVE_PASS'))
GDTOT_CRYPT= str(getenv('GDTOT_CRYPT'))
