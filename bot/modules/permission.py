from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, is_gdrive_link
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def permissionNode(update, context):
    args = update.message.text.split()
    reply_to = update.message.reply_to_message
    link = ''
    access = ''
    if len(args) > 1:
        link = args[1].strip()
        try:
            access = args[2].strip()
        except IndexError:
            pass
    if reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
        try:
            access = args[1].strip()
        except IndexError:
            pass
    if is_gdrive_link(link):
        msg = sendMessage(f"<b>Setting permission:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Setting permission: {link}")
        gd = GoogleDriveHelper()
        result = gd.setPermission(link, access)
        deleteMessage(context.bot, msg)
        sendMessage(result, context.bot, update.message)
    else:
        sendMessage("<b>Send a Drive link along with command</b>", context.bot, update.message)

permission_handler = CommandHandler(BotCommands.PermissionCommand, permissionNode,
                                    filters=CustomFilters.owner_filter)
dispatcher.add_handler(permission_handler)
