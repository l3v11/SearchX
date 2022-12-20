from telegram.ext import CommandHandler

from bot import dispatcher, AUTHORIZED_USERS, DATABASE_URL
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.database import DatabaseHelper

def authorize(update, context):
    user_id = ''
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        user_id = int(context.args[0])
    elif reply_message:
        user_id = reply_message.from_user.id
    else:
        user_id = update.effective_chat.id
    if user_id in AUTHORIZED_USERS:
        msg = 'Already authorized'
    elif DATABASE_URL is not None:
        msg = DatabaseHelper().auth_user(user_id)
        AUTHORIZED_USERS.add(user_id)
    else:
        AUTHORIZED_USERS.add(user_id)
        msg = 'Authorization granted'
    sendMessage(msg, context.bot, update.message)

def unauthorize(update, context):
    user_id = ''
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        user_id = int(context.args[0])
    elif reply_message:
        user_id = reply_message.from_user.id
    else:
        user_id = update.effective_chat.id
    if user_id in AUTHORIZED_USERS:
        if DATABASE_URL is not None:
            msg = DatabaseHelper().unauth_user(user_id)
        else:
            msg = 'Authorization revoked'
        AUTHORIZED_USERS.remove(user_id)
    else:
        msg = 'Already unauthorized'
    sendMessage(msg, context.bot, update.message)

def auth_users(update, context):
    users = ''
    users += 'None' if len(AUTHORIZED_USERS) == 0 else '\n'.join(f'<code>{user}</code>' for user in AUTHORIZED_USERS)
    msg = f'<b><u>Authorized Users</u></b>\n{users}'
    sendMessage(msg, context.bot, update.message)

authorize_handler = CommandHandler(BotCommands.AuthorizeCommand, authorize,
                                   filters=CustomFilters.owner_filter)
unauthorize_handler = CommandHandler(BotCommands.UnauthorizeCommand, unauthorize,
                                     filters=CustomFilters.owner_filter)
users_handler = CommandHandler(BotCommands.UsersCommand, auth_users,
                               filters=CustomFilters.owner_filter)
dispatcher.add_handler(authorize_handler)
dispatcher.add_handler(unauthorize_handler)
dispatcher.add_handler(users_handler)
