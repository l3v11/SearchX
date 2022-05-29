from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage

def list_drive(update, context):
    LOGGER.info(f"User: {update.message.from_user.first_name} [{update.message.from_user.id}]")
    args = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message
    query = ''
    if len(args) > 1:
        query = args[1]
    if reply_to is not None:
        query = reply_to.text
    if query != '':
        reply = sendMessage(f"<b>Finding:</b> <code>{query}</code>", context.bot, update.message)
        LOGGER.info(f"Finding: {query}")
        gd = GoogleDriveHelper()
        try:
            msg, button = gd.drive_list(query)
        except Exception as e:
            msg, button = "There was an error", None
            LOGGER.exception(e)
        editMessage(msg, reply, button)
    else:
        sendMessage('<b>Send a Query along with command</b>', context.bot, update.message)
        LOGGER.info("Finding: None")

list_handler = CommandHandler(BotCommands.ListCommand, list_drive,
                              filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(list_handler)
