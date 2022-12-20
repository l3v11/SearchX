from telegram.ext import CommandHandler

from bot import dispatcher, OWNER_ID, download_dict, download_dict_lock
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.bot_utils import getDownloadByGid

def cancelNode(update, context):
    user_id = update.message.from_user.id
    if len(context.args) == 1:
        gid = context.args[0]
        dl = getDownloadByGid(gid)
        if not dl:
            sendMessage(f"<b>GID:</b> <code>{gid}</code> not found", context.bot, update.message)
            return
    elif update.message.reply_to_message:
        task_message = update.message.reply_to_message
        with download_dict_lock:
            if task_message.message_id in download_dict:
                dl = download_dict[task_message.message_id]
            else:
                dl = None
        if not dl:
            sendMessage("Not an active task", context.bot, update.message)
            return
    elif len(context.args) == 0:
        sendMessage("<b>Send a GID along with command</b>", context.bot, update.message)
        return
    if OWNER_ID != user_id and dl.message.from_user.id != user_id:
        sendMessage("Not your task", context.bot, update.message)
        return
    dl.download().cancel_task()

cancel_handler = CommandHandler(BotCommands.CancelCommand, cancelNode,
                                filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(cancel_handler)
