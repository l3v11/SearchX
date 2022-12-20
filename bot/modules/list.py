from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage

def list_drive(update, context):
    args = update.message.text.split(maxsplit=1)
    reply_to = update.message.reply_to_message
    query = ''
    if len(args) > 1:
        query = args[1].strip()
    if reply_to is not None:
        query = reply_to.text.strip()
    if query != '':
        reply = sendMessage(f"<b>Search in progress...</b>", context.bot, update.message)
        LOGGER.info(f"Finding: {query}")
        gd = GoogleDriveHelper()
        try:
            msg, button = gd.drive_list(query)
        except Exception as err:
            msg, button = "Internal error", None
            LOGGER.error(err)
        editMessage(msg, reply, button)
    else:
        help_msg = '<b><u>Instructions</u></b>\nSend a Query along with command'
        help_msg += '\n\n<b><u>Get Folder Results</u></b>\nAdd "<code>-d</code>" before the Query'
        help_msg += '\n\n<b><u>Get File Results</u></b>\nAdd "<code>-f</code>" before the Query'
        sendMessage(help_msg, context.bot, update.message)

list_handler = CommandHandler(BotCommands.ListCommand, list_drive,
                              filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(list_handler)
