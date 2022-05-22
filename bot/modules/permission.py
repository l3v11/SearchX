from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, is_gdrive_link
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def permissionNode(update, context):
    LOGGER.info(f"User: {update.message.from_user.first_name} [{update.message.from_user.id}]")
    args = update.message.text.split(" ", maxsplit=2)
    link = ''
    access = ''
    if len(args) > 1:
        link = args[1]
        try:
            access = args[2]
        except IndexError:
            access = "anyone"
    if is_gdrive_link(link):
        msg = sendMessage(f"<b>Setting permission:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Setting permission: {link}")
        gd = GoogleDriveHelper()
        result = gd.setPerm(link, access)
        deleteMessage(context.bot, msg)
        sendMessage(result, context.bot, update.message)
    else:
        sendMessage("<b>Send a Drive link along with command</b>", context.bot, update.message)
        LOGGER.info("Setting permission: None")

permission_handler = CommandHandler(BotCommands.PermissionCommand, permissionNode,
                                filters=CustomFilters.owner_filter, run_async=True)
dispatcher.add_handler(permission_handler)
