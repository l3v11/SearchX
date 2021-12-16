from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def countNode(update, context):
    LOGGER.info('User: {} [{}]'.format(update.message.from_user.first_name, update.message.from_user.id))
    args = update.message.text.split(" ", maxsplit=1)
    if len(args) > 1:
        link = args[1]
        msg = sendMessage(f"<b>Counting:</b> <code>{link}</code>", context.bot, update)
        gd = GoogleDriveHelper()
        result = gd.count(link)
        deleteMessage(context.bot, msg)
        sendMessage(result, context.bot, update)
    else:
        sendMessage("Send a drive link along with command", context.bot, update)

count_handler = CommandHandler(BotCommands.CountCommand, countNode,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(count_handler)
