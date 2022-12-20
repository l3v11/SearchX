from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, is_gdrive_link
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def countNode(update, context):
    reply_to = update.message.reply_to_message
    link = ''
    if len(context.args) == 1:
        link = context.args[0]
    if reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    if is_gdrive_link(link):
        msg = sendMessage(f"<b>Counting:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Counting: {link}")
        gd = GoogleDriveHelper()
        result = gd.count(link)
        deleteMessage(context.bot, msg)
        sendMessage(result, context.bot, update.message)
    else:
        sendMessage("<b>Send a Drive link along with command</b>", context.bot, update.message)

count_handler = CommandHandler(BotCommands.CountCommand, countNode,
                               filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(count_handler)
