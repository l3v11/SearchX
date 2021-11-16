from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands

def cloneNode(update,context):
    LOGGER.info('User: {} [{}]'.format(update.message.chat.first_name, update.message.chat_id))
    args = update.message.text.split(" ",maxsplit=1)
    if len(args) > 1:
        link = args[1]
        msg = sendMessage(f"Cloning: <code>{link}</code>",context.bot,update)
        gd = GoogleDriveHelper()
        result = gd.clone(link)
        deleteMessage(context.bot,msg)
        sendMessage(result,context.bot,update)
    else:
        sendMessage("Send a drive link along with command",context.bot,update)

clone_handler = CommandHandler(BotCommands.CloneCommand,cloneNode,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
