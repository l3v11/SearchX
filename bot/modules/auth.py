from telegram.ext import CommandHandler

from bot import AUTHORIZED_CHATS, dispatcher
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage

def auth_chats(update, context):
    users = ''
    for user in AUTHORIZED_CHATS:
        users += f"{user}\n"
    users = users if users != '' else "None"
    sendMessage(f'<b><u>Authorized Chats</u></b>\n<code>{users}</code>\n', context.bot, update)

auth_handler = CommandHandler(BotCommands.AuthUsersCommand, auth_chats,
                              filters=CustomFilters.owner_filter, run_async=True)
dispatcher.add_handler(auth_handler)
