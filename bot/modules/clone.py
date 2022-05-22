import random
import string

from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher, CLONE_LIMIT, download_dict, download_dict_lock, Interval
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, get_readable_file_size, is_gdrive_link, \
    is_appdrive_link, is_gdtot_link
from bot.helper.ext_utils.clone_status import CloneStatus
from bot.helper.ext_utils.exceptions import ExceptionHandler
from bot.helper.ext_utils.parser import appdrive, gdtot
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, \
    delete_all_messages, update_all_messages, sendStatusMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def cloneNode(update, context):
    LOGGER.info(f"User: {update.message.from_user.first_name} [{update.message.from_user.id}]")
    args = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message
    link = ''
    if len(args) > 1:
        link = args[1]
    if reply_to is not None:
        if len(link) == 0:
            link = reply_to.text
    is_appdrive = is_appdrive_link(link)
    is_gdtot = is_gdtot_link(link)
    if (is_appdrive or is_gdtot):
        msg = sendMessage(f"<b>Processing:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Processing: {link}")
        try:
            if is_appdrive:
                appdict = appdrive(link)
                link = appdict.get('gdrive_link')
            if is_gdtot:
                link = gdtot(link)
            deleteMessage(context.bot, msg)
        except ExceptionHandler as e:
            deleteMessage(context.bot, msg)
            LOGGER.error(e)
            return sendMessage(str(e), context.bot, update.message)
    if is_gdrive_link(link):
        msg = sendMessage(f"<b>Checking:</b> <code>{link}</code>", context.bot, update.message)
        gd = GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        deleteMessage(context.bot, msg)
        if res != "":
            return sendMessage(res, context.bot, update.message)
        if CLONE_LIMIT is not None:
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f"<b>Name:</b> <code>{name}</code>"
                msg2 += f"\n<b>Size:</b> {get_readable_file_size(size)}"
                msg2 += f"\n<b>Limit:</b> {CLONE_LIMIT} GiB"
                msg2 += "\n\n<b>⚠️ Task failed</b>"
                return sendMessage(msg2, context.bot, update.message)
        if files <= 20:
            msg = sendMessage(f"<b>Cloning:</b> <code>{link}</code>", context.bot, update.message)
            LOGGER.info(f"Cloning: {link}")
            result = gd.clone(link)
            deleteMessage(context.bot, msg)
        else:
            drive = GoogleDriveHelper(name)
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
            clone_status = CloneStatus(drive, size, files, update.message, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update.message, context.bot)
            LOGGER.info(f"Cloning: {link}")
            result = drive.clone(link)
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
        elif is_appdrive:
            if appdict.get('link_type') == 'login':
                LOGGER.info(f"Deleting: {link}")
                gd.deleteFile(link)
    else:
        sendMessage("<b>Send a Drive / AppDrive / DriveApp / GDToT link along with command</b>", context.bot, update.message)
        LOGGER.info("Cloning: None")

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
