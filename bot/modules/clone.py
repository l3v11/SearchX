import time

from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, is_gdrive_link, is_appdrive_link, is_gdtot_link
from bot.helper.ext_utils.clone_status import CloneStatus
from bot.helper.ext_utils.exceptions import ExceptionHandler
from bot.helper.ext_utils.parser import appdrive, gdtot
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def cloneNode(update, context):
    LOGGER.info('User: {} [{}]'.format(update.message.from_user.first_name, update.message.from_user.id))
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
        try:
            msg = sendMessage(f"<b>Processing:</b> <code>{link}</code>", context.bot, update)
            LOGGER.info(f"Processing: {link}")
            if is_appdrive:
                appdict = appdrive(link)
                link = appdict.get('gdrive_link')
            if is_gdtot:
                link = gdtot(link)
            deleteMessage(context.bot, msg)
        except ExceptionHandler as e:
            deleteMessage(context.bot, msg)
            LOGGER.error(e)
            return sendMessage(str(e), context.bot, update)
    if is_gdrive_link(link):
        msg = sendMessage(f"<b>Cloning:</b> <code>{link}</code>", context.bot, update)
        LOGGER.info(f"Cloning: {link}")
        status_class = CloneStatus()
        gd = GoogleDriveHelper()
        sendCloneStatus(link, msg, status_class, update, context)
        result = gd.clone(link, status_class)
        deleteMessage(context.bot, msg)
        status_class.set_status(True)
        sendMessage(result, context.bot, update)
        if is_gdtot:
            LOGGER.info(f"Deleting: {link}")
            gd.deleteFile(link)
        if is_appdrive:
            if appdict.get('link_type') == 'login':
                LOGGER.info(f"Deleting: {link}")
                gd.deleteFile(link)
    else:
        sendMessage("<b>Send a Drive / AppDrive / DriveApp / GDToT link along with command</b>", context.bot, update)
        LOGGER.info("Cloning: None")

@new_thread
def sendCloneStatus(link, msg, status, update, context):
    old_statmsg = ''
    while not status.done():
        time.sleep(3)
        try:
            statmsg = f"<b>Cloning:</b> <a href='{status.source_folder_link}'>{status.source_folder_name}</a>\n━━━━━━━━━━━━━━" \
                      f"\n<b>Current file:</b> <code>{status.get_name()}</code>\n\n<b>Transferred</b>: <code>{status.get_size()}</code>"
            if not statmsg == old_statmsg:
                editMessage(statmsg, msg)
                old_statmsg = statmsg
        except Exception as e:
            if str(e) == "Message to edit not found":
                break
            time.sleep(2)
            continue
    return

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
