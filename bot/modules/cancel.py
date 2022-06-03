from telegram.ext import CommandHandler

from bot import dispatcher, OWNER_ID, download_dict, download_dict_lock
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.bot_utils import TaskStatus, getDownloadByGid

def cancelNode(update, context):
    args = update.message.text.split(" ", maxsplit=1)
    user_id = update.message.from_user.id
    if len(args) > 1:
        gid = args[1]
        dl = getDownloadByGid(gid)
        if not dl:
            return sendMessage(f"<b>GID:</b> <code>{gid}</code> not found", context.bot, update.message)
    elif update.message.reply_to_message:
        task_message = update.message.reply_to_message
        with download_dict_lock:
            keys = list(download_dict.keys())
            if task_message.message_id in keys:
                dl = download_dict[task_message.message_id]
            else:
                dl = None
        if not dl:
            return sendMessage("Not an active task", context.bot, update.message)
    elif len(args) == 1:
        return sendMessage("<b>Send a GID along with command</b>", context.bot, update.message)
    if OWNER_ID != user_id and dl.message.from_user.id != user_id:
        return sendMessage("Not your task", context.bot, update.message)
    if dl.status() == TaskStatus.STATUS_ARCHIVING:
        sendMessage("Archival in progress, the task cannot be cancelled", context.bot, update.message)
    elif dl.status() == TaskStatus.STATUS_EXTRACTING:
        sendMessage("Extraction in progress, the task cannot be cancelled", context.bot, update.message)
    else:
        dl.download().cancel_task()

cancel_handler = CommandHandler(BotCommands.CancelCommand, cancelNode,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(cancel_handler)
