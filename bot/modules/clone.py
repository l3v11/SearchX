import random
import string

from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher, Interval, BOOKMARKS, CLONE_LIMIT, download_dict, download_dict_lock
from bot.helper.download_utils.ddl_generator import gdtot
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, get_readable_file_size, is_gdrive_link, is_gdtot_link
from bot.helper.ext_utils.exceptions import DDLExceptionHandler
from bot.helper.status_utils.clone_status import CloneStatus
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, delete_all_messages, \
    update_all_messages, sendStatusMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def cloneNode(update, context):
    args = update.message.text.split()
    reply_to = update.message.reply_to_message
    link = ''
    key = ''
    dest_id = ''
    if len(args) > 1:
        link = args[1].strip()
        try:
            key = args[2].strip()
            try:
                dest_id = BOOKMARKS[key]
            except KeyError:
                return sendMessage("Invalid Drive Key", context.bot, update.message)
        except IndexError:
            pass
    if reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
        try:
            key = args[1].strip()
            try:
                dest_id = BOOKMARKS[key]
            except KeyError:
                return sendMessage("Invalid Drive Key", context.bot, update.message)
        except IndexError:
            pass
    is_gdtot = is_gdtot_link(link)
    if is_gdtot:
        msg = sendMessage(f"<b>Processing:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Processing: {link}")
        try:
            link = gdtot(link)
            deleteMessage(context.bot, msg)
        except DDLExceptionHandler as err:
            deleteMessage(context.bot, msg)
            LOGGER.error(err)
            return sendMessage(str(err), context.bot, update.message)
    if is_gdrive_link(link):
        msg = sendMessage(f"<b>Checking:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Checking: {link}")
        gd = GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        deleteMessage(context.bot, msg)
        if res != "":
            return sendMessage(res, context.bot, update.message)
        if CLONE_LIMIT is not None:
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f"<b>Name:</b> <code>{name}</code>"
                msg2 += f"\n<b>Size:</b> {get_readable_file_size(size)}"
                msg2 += f"\n<b>Limit:</b> {CLONE_LIMIT} GB"
                msg2 += "\n\n<b>⚠️ Task failed</b>"
                return sendMessage(msg2, context.bot, update.message)
        if files <= 20:
            msg = sendMessage(f"<b>Cloning:</b> <code>{link}</code>", context.bot, update.message)
            LOGGER.info(f"Cloning: {link}")
            result = gd.clone(link, dest_id)
            deleteMessage(context.bot, msg)
        else:
            drive = GoogleDriveHelper(name)
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
            clone_status = CloneStatus(drive, size, update.message, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update.message, context.bot)
            LOGGER.info(f"Cloning: {link}")
            result = drive.clone(link, dest_id)
            with download_dict_lock:
                del download_dict[update.message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        sendMessage(result, context.bot, update.message)
        if is_gdtot:
            LOGGER.info(f"Deleting: {link}")
            gd.deleteFile(link)
    else:
        help_msg = '<b><u>Instructions</u></b>\nSend a link along with command'
        help_msg += '\n\n<b><u>Supported Sites</u></b>\n• Google Drive\n• GDToT'
        sendMessage(help_msg, context.bot, update.message)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode,
                               filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(clone_handler)
