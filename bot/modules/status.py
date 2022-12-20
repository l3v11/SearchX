import time

from telegram.ext import CommandHandler

from bot import dispatcher, Interval, STATUS_UPDATE_INTERVAL, download_dict, \
    download_dict_lock, status_reply_dict_lock
from bot.helper.ext_utils.bot_utils import SetInterval
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, \
    update_all_messages, sendStatusMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

def statusNode(update, context):
    with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        return sendMessage("<b>No active task</b>", context.bot, update.message)
    else:
        sendStatusMessage(update.message, context.bot)
        deleteMessage(context.bot, update.message)
        with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(SetInterval(STATUS_UPDATE_INTERVAL, update_all_messages))

status_handler = CommandHandler(BotCommands.StatusCommand, statusNode,
                                filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(status_handler)
