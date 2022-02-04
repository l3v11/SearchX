from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, is_gdrive_link, is_gdtot_link, is_appdrive_link
from bot.helper.ext_utils.parser import appdrive, gdtot
from bot.helper.ext_utils.exceptions import DDLException
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def cloneNode(update, context):
    LOGGER.info('User: {} [{}]'.format(update.message.from_user.first_name, update.message.from_user.id))
    args = update.message.text.split(" ", maxsplit=1)
    if len(args) > 1:
        link = args[1]
    else:
        link = ''
    try:
        msg = sendMessage(f"<b>Processing:</b> <code>{link}</code>", context.bot, update)
        LOGGER.info(f"Processing: {link}")
        is_gdtot = is_gdtot_link(link)
        if is_gdtot:
            link = gdtot(link)
        is_appdrive = is_appdrive_link(link)
        if is_appdrive:
            apdict = appdrive(link)
            link = apdict.get('gdrive_link')
        deleteMessage(context.bot, msg)
    except DDLException as e:
        deleteMessage(context.bot, msg)
        LOGGER.error(e)
        return sendMessage(str(e), context.bot, update)
    if is_gdrive_link(link):
        msg = sendMessage(f"<b>Cloning:</b> <code>{link}</code>", context.bot, update)
        LOGGER.info(f"Cloning: {link}")
        gd = GoogleDriveHelper()
        result = gd.clone(link)
        deleteMessage(context.bot, msg)
        sendMessage(result, context.bot, update)
        if is_gdtot:
            LOGGER.info(f"Deleting: {link}")
            gd.deleteFile(link)
        elif is_appdrive:
            if apdict.get('link_type') == 'login':
                LOGGER.info(f"Deleting: {link}")
                gd.deleteFile(link)
    else:
        sendMessage("Send a drive or gdtot link along with command", context.bot, update)
        LOGGER.info("Cloning: None")

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
