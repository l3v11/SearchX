import mimetypes
import requests
import subprocess

from telegram.ext import CommandHandler
from urllib.parse import unquote_plus

from bot import LOGGER, TELEGRAPH, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, get_readable_file_size, is_url, is_gdrive_link
from bot.helper.ext_utils.exceptions import DDLExceptionHandler
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_builder import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def mediainfoNode(update, context):
    reply_to = update.message.reply_to_message
    link = ''
    if len(context.args) == 1:
        link = context.args[0]
    if reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    if is_url(link):
        msg = sendMessage(f"<b>Getting mediainfo:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Getting mediainfo: {link}")
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
                header = f"--file_curl=HttpHeader,Authorization: Bearer {access_token}"
                out = subprocess.run(f"mediainfo '{header}' {file_dl}", capture_output=True, shell=True)
                stderr = out.stderr.decode('utf-8')
                if "downloadQuotaExceeded" in stderr or "cannotDownloadFile" in stderr:
                    raise DDLExceptionHandler("Download quota exceeded")
                stdout = out.stdout.decode('utf-8')
                metadata = stdout.replace(file_dl.replace("\\", ""), name)
                page = TELEGRAPH[0].create_page(
                    title='SearchX Mediainfo',
                    author_name='Levi',
                    author_url='https://t.me/l3v11',
                    html_content=f'<pre>{metadata}</pre>')['path']
                result = ""
                result += f"<b>Name:</b> <code>{name}</code>"
                result += f"\n<b>Size:</b> <code>{size}</code>"
                result += f"\n<b>Type:</b> <code>{mime_type}</code>"
                button = ButtonMaker()
                button.build_button("VIEW MEDIAINFO 🗂️", f"https://graph.org/{page}")
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
                out = subprocess.run(["mediainfo", f"{link}"], capture_output=True)
                stdout = out.stdout.decode('utf-8')
                metadata = stdout.replace(link, name)
                page = TELEGRAPH[0].create_page(
                    title='SearchX Mediainfo',
                    author_name='Levi',
                    author_url='https://t.me/l3v11',
                    html_content=f'<pre>{metadata}</pre>')['path']
                result = ""
                result += f"<b>Name:</b> <code>{name}</code>"
                result += f"\n<b>Size:</b> <code>{size}</code>"
                result += f"\n<b>Type:</b> <code>{mime_type}</code>"
                button = ButtonMaker()
                button.build_button("VIEW MEDIAINFO 🗂️", f"https://graph.org/{page}")
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

mediainfo_handler = CommandHandler(BotCommands.MediainfoCommand, mediainfoNode,
                                   filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(mediainfo_handler)
