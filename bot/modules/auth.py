from telegram.ext import CommandHandler

from bot import dispatcher, AUTHORIZED_CHATS, DATABASE_URL
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.database import DatabaseHelper

def authorize(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        # Authorize an user in private
        user_id = int(context.args[0])
        if user_id in AUTHORIZED_CHATS:
            msg = 'Already authorized'
        elif DATABASE_URL is not None:
            msg = DatabaseHelper().auth_user(user_id)
            AUTHORIZED_CHATS.add(user_id)
        else:
            AUTHORIZED_CHATS.add(user_id)
            msg = 'Authorization granted'
    elif reply_message:
        # Authorize an user by replying
        user_id = reply_message.from_user.id
        if user_id in AUTHORIZED_CHATS:
            msg = 'Already authorized'
        elif DATABASE_URL is not None:
            msg = DatabaseHelper().auth_user(user_id)
            AUTHORIZED_CHATS.add(user_id)
        else:
            AUTHORIZED_CHATS.add(user_id)
            msg = 'Authorization granted'
    else:
        # Authorize a chat
        chat_id = update.effective_chat.id
        if chat_id in AUTHORIZED_CHATS:
            msg = 'Already authorized'
        elif DATABASE_URL is not None:
            msg = DatabaseHelper().auth_user(chat_id)
            AUTHORIZED_CHATS.add(chat_id)
        else:
            AUTHORIZED_CHATS.add(chat_id)
            msg = 'Authorization granted'
    sendMessage(msg, context.bot, update.message)

def unauthorize(update, context):
    reply_message = update.message.reply_to_message
    if len(context.args) == 1:
        # Unauthorize an user in private
        user_id = int(context.args[0])
        if user_id in AUTHORIZED_CHATS:
            if DATABASE_URL is not None:
                msg = DatabaseHelper().unauth_user(user_id)
            else:
                msg = 'Authorization revoked'
            AUTHORIZED_CHATS.remove(user_id)
        else:
            msg = 'Already unauthorized'
    elif reply_message:
        # Unauthorize an user by replying
        user_id = reply_message.from_user.id
        if user_id in AUTHORIZED_CHATS:
            if DATABASE_URL is not None:
                msg = DatabaseHelper().unauth_user(user_id)
            else:
                msg = 'Authorization revoked'
            AUTHORIZED_CHATS.remove(user_id)
        else:
            msg = 'Already unauthorized'
    else:
        # Unauthorize a chat
        chat_id = update.effective_chat.id
        if chat_id in AUTHORIZED_CHATS:
            if DATABASE_URL is not None:
                msg = DatabaseHelper().unauth_user(chat_id)
            else:
                msg = 'Authorization revoked'
            AUTHORIZED_CHATS.remove(chat_id)
        else:
            msg = 'Already unauthorized'
    sendMessage(msg, context.bot, update.message)

def auth_chats(update, context):
    users = ''
    users += '\n'.join(f"<code>{uid}</code>" for uid in AUTHORIZED_CHATS)
    msg = f'<b><u>Authorized Chats</u></b>\n{users}'
    sendMessage(msg, context.bot, update.message)

authorize_handler = CommandHandler(BotCommands.AuthorizeCommand, authorize,
                                   filters=CustomFilters.owner_filter, run_async=True)
unauthorize_handler = CommandHandler(BotCommands.UnauthorizeCommand, unauthorize,
                                    filters=CustomFilters.owner_filter, run_async=True)
auth_handler = CommandHandler(BotCommands.UsersCommand, auth_chats,
                              filters=CustomFilters.owner_filter, run_async=True)
dispatcher.add_handler(authorize_handler)
dispatcher.add_handler(unauthorize_handler)
dispatcher.add_handler(auth_handler)
