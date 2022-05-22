import time

from psutil import cpu_percent, virtual_memory
from telegram.ext import CommandHandler

from bot import dispatcher, botStartTime, download_dict, download_dict_lock, status_reply_dict, status_reply_dict_lock
from bot.helper.ext_utils.bot_utils import get_readable_time
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, sendStatusMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

def statusNode(update, context):
    with download_dict_lock:
        if len(download_dict) == 0:
            message = "No active task\n━━━━━━━━━━━━━━━"
            message += f"\n<b>CPU:</b> {cpu_percent()}% | <b>RAM:</b> {virtual_memory().percent}%"
            message += f"\n<b>UPTIME:</b> {get_readable_time(time.time() - botStartTime)}"
            return sendMessage(message, context.bot, update.message)
    index = update.effective_chat.id
    with status_reply_dict_lock:
        if index in status_reply_dict.keys():
            deleteMessage(context.bot, status_reply_dict[index])
            del status_reply_dict[index]
    sendStatusMessage(update.message, context.bot)
    deleteMessage(context.bot, update.message)

status_handler = CommandHandler(BotCommands.StatusCommand, statusNode,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(status_handler)
