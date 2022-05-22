from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage

def list_drive(update, context):
    LOGGER.info(f"User: {update.message.from_user.first_name} [{update.message.from_user.id}]")
    try:
        search = update.message.text.split(' ', maxsplit=1)[1]
    except IndexError:
        sendMessage('<b>Send a Query along with command</b>', context.bot, update.message)
        LOGGER.info("Query: None")
        return
    reply = sendMessage('<b>Search in progress...</b>', context.bot, update.message)
    LOGGER.info(f"Query: {search}")
    gd = GoogleDriveHelper()
    try:
        msg, button = gd.drive_list(search)
    except Exception as e:
        msg, button = "There was an error", None
        LOGGER.exception(e)
    editMessage(msg, reply, button)

list_handler = CommandHandler(BotCommands.ListCommand, list_drive,
                              filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(list_handler)
