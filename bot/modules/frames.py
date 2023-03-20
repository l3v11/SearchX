import mimetypes
import os
import random
import requests
import string
import subprocess

from telegram.ext import CommandHandler
from urllib.parse import unquote_plus

from bot import LOGGER, DOWNLOAD_DIR, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, get_readable_file_size, slowpics_collection, is_url, is_gdrive_link
from bot.helper.ext_utils.exceptions import DDLExceptionHandler
from bot.helper.ext_utils.fs_utils import clean_download
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_builder import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def framesNode(update, context):
    args = update.message.text.split()
    reply_to = update.message.reply_to_message
    link = ''
    frames = 5
    if len(args) > 1:
        link = args[1].strip()
        try:
            frames = int(args[2])
        except (IndexError, ValueError):
            pass
    if reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
        try:
            frames = int(args[1])
        except (IndexError, ValueError):
            pass
    if frames > 10:
        frames = 10
    if is_url(link):
        msg = sendMessage(f"<b>Getting {frames} frames:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Getting {frames} frames: {link}")
        if is_gdrive_link(link):
            try:
                gd = GoogleDriveHelper()
                res, file_id, access_token, name, size, mime_type = gd.fileinfo(link)
                if res != "":
                    deleteMessage(context.bot, msg)
                    return sendMessage(res, context.bot, update.message)
                if mime_type == "application/vnd.google-apps.folder":
                    raise DDLExceptionHandler("Folder is not supported")
                file_dl = f"https://www.googleapis.com/drive/v3/files/{file_id}\?supportsAllDrives\=true\&alt\=media"
                header = f"Authorization: Bearer {access_token}"
                out = subprocess.run(f"ffprobe -headers '{header}' -i {file_dl} -show_entries format=duration -v error -of csv=p=0", capture_output=True, shell=True)
                stderr = out.stderr.decode('utf-8')
                if "403 Forbidden" in stderr:
                    raise DDLExceptionHandler("Download quota exceeded")
                duration = out.stdout.decode('utf-8')
                if duration == '':
                    raise ValueError("Unsupported media file")
                uid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
                path = f"{DOWNLOAD_DIR}{uid}"
                os.makedirs(path)
                for seconds in random.sample(range(int(float(duration))), int(f"{frames}")):
                    img = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=3))
                    genss = subprocess.run(f"ffmpeg -headers '{header}' -hide_banner -ss {seconds} -i {file_dl} -frames:v 1 -q:v 2 -y {path}/{img}.png", capture_output=True, shell=True)
                    if "403 Forbidden" in genss.stderr.decode('utf-8'):
                        raise DDLExceptionHandler("Download quota exceeded")
                img_link = slowpics_collection(path)
                result = ""
                result += f"<b>Name:</b> <code>{name}</code>"
                result += f"\n<b>Size:</b> <code>{size}</code>"
                result += f"\n<b>Type:</b> <code>{mime_type}</code>"
                button = ButtonMaker()
                button.build_button("VIEW FRAMES 🗂️", f"{img_link}")
                clean_download(path)
                deleteMessage(context.bot, msg)
                sendMessage(result, context.bot, update.message, button.build_menu(1))
            except Exception as err:
                deleteMessage(context.bot, msg)
                LOGGER.error(str(err))
                return sendMessage(str(err), context.bot, update.message)
        else:
            try:
                res = requests.head(link, stream=True)
                name = unquote_plus(link).rsplit('/', 1)[-1]
                size = get_readable_file_size(int(res.headers["Content-Length"].strip()))
                mime_type = res.headers.get("Content-Type", mimetypes.guess_type(name)).rsplit(";", 1)[0]
                out = subprocess.run(["ffprobe", "-i", f"{link}", "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"], capture_output=True)
                duration = out.stdout.decode('utf-8')
                if duration == '':
                    raise ValueError("Unsupported media file")
                uid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
                path = f"{DOWNLOAD_DIR}{uid}"
                os.makedirs(path)
                sscount=1
                for seconds in random.sample(range(int(float(duration))), int(f"{frames}")):
                    img = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=4))
                    genss = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{seconds}", "-i", f"{link}", "-frames:v", "1", "-q:v", "2", "-y", f"{path}/{img}.png"], capture_output=True)
                    sscount+=1
                img_link = slowpics_collection(path)
                result = ""
                result += f"<b>Name:</b> <code>{name}</code>"
                result += f"\n<b>Size:</b> <code>{size}</code>"
                result += f"\n<b>Type:</b> <code>{mime_type}</code>"
                button = ButtonMaker()
                button.build_button("VIEW FRAMES 🗂️", f"{img_link}")
                clean_download(path)
                deleteMessage(context.bot, msg)
                sendMessage(result, context.bot, update.message, button.build_menu(1))
            except KeyError:
                deleteMessage(context.bot, msg)
                err = "Invalid link"
                LOGGER.error(str(err))
                return sendMessage(str(err), context.bot, update.message)
            except Exception as err:
                deleteMessage(context.bot, msg)
                LOGGER.error(str(err))
                return sendMessage(str(err), context.bot, update.message)
    else:
        sendMessage("<b>Send a link along with command</b>", context.bot, update.message)

frames_handler = CommandHandler(BotCommands.FramesCommand, framesNode,
                                filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(frames_handler)
