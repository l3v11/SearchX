import threading

from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

def deleteNode(update, context):
    LOGGER.info('User: {} [{}]'.format(update.message.chat.first_name, update.message.chat_id))
    args = update.message.text.split(" ", maxsplit=1)
    if len(args) > 1:
        link = args[1]
        gd = GoogleDriveHelper()
        msg = gd.deletefile(link)
    else:
        msg = 'Send a drive link along with command'
    reply_message = sendMessage(msg, context.bot, update)
    threading.Thread(args=(context.bot, update.message, reply_message)).start()

delete_handler = CommandHandler(BotCommands.DeleteCommand, deleteNode,
                                filters=CustomFilters.owner_filter, run_async=True)
dispatcher.add_handler(delete_handler)
