from telegram.ext import CommandHandler

from bot import AUTHORIZED_CHATS, dispatcher, updater
from bot.modules import auth, list, shell
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import *

def start(update, context):
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        if update.message.chat.type == "private":
            sendMessage(f"Access granted", context.bot, update)
        else:
            sendMessage(f"This is a bot for searching data on Google Drive", context.bot, update)
    else:
        sendMessage(f"Access denied", context.bot, update)

def log(update, context):
    send_log_file(context.bot, update)

def main():
    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log,
                                 filters=CustomFilters.owner_filter, run_async=True)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(log_handler)

    updater.start_polling()
    LOGGER.info("Bot started")
    updater.idle()

main()
