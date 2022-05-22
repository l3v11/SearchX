from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher, OWNER_ID, download_dict, download_dict_lock
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.bot_utils import getDownloadByGid

def cancelNode(update, context):
    LOGGER.info(f"User: {update.message.from_user.first_name} [{update.message.from_user.id}]")
    args = update.message.text.split(" ", maxsplit=1)
    user_id = update.message.from_user.id
    if len(args) > 1:
        gid = args[1]
        dl = getDownloadByGid(gid)
        if not dl:
            LOGGER.info("Cancelling: None")
            return sendMessage(f"<b>GID:</b> <code>{gid}</code> not found", context.bot, update.message)
    elif update.message.reply_to_message:
        task_message = update.message.reply_to_message
        with download_dict_lock:
            keys = list(download_dict.keys())
            try:
                dl = download_dict[task_message.message_id]
            except:
                dl = None
        if not dl:
            LOGGER.info("Cancelling: None")
            return sendMessage("Not an active task", context.bot, update.message)
    elif len(args) == 1:
        msg = "<b>Send a GID along with command</b>"
        LOGGER.info("Cancelling: None")
        return sendMessage(msg, context.bot, update.message)
    if OWNER_ID != user_id and dl.message.from_user.id != user_id:
        LOGGER.info("Cancelling: None")
        return sendMessage("Not your task", context.bot, update.message)
    else:
        dl.download().cancel_task()

cancel_handler = CommandHandler(BotCommands.CancelCommand, cancelNode,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(cancel_handler)
