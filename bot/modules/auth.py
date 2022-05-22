from telegram.ext import CommandHandler

from bot import AUTHORIZED_CHATS, DATABASE_URL, dispatcher
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.database import DatabaseHelper

def authorize(update, context):
    reply_message = None
    message_ = None
    reply_message = update.message.reply_to_message
    message_ = update.message.text.split(' ')
    if len(message_) == 2:
        # Trying to authorize an user in private
        user_id = int(message_[1])
        if user_id in AUTHORIZED_CHATS:
            msg = 'Already authorized'
        elif DATABASE_URL is not None:
            db = DatabaseHelper()
            msg = db.auth_user(user_id)
            AUTHORIZED_CHATS.add(user_id)
        else:
            AUTHORIZED_CHATS.add(user_id)
            with open('authorized_chats.txt', 'a') as file:
                file.write(f'{user_id}\n')
                msg = 'Authorization granted'
    elif reply_message is None:
        # Trying to authorize a chat
        chat_id = update.effective_chat.id
        if chat_id in AUTHORIZED_CHATS:
            msg = 'Already authorized'
        elif DATABASE_URL is not None:
            db = DatabaseHelper()
            msg = db.auth_user(chat_id)
            AUTHORIZED_CHATS.add(chat_id)
        else:
            AUTHORIZED_CHATS.add(chat_id)
            with open('authorized_chats.txt', 'a') as file:
                file.write(f'{chat_id}\n')
                msg = 'Authorization granted'
    else:
        # Trying to authorize an user by replying
        user_id = reply_message.from_user.id
        if user_id in AUTHORIZED_CHATS:
            msg = 'Already authorized'
        elif DATABASE_URL is not None:
            db = DatabaseHelper()
            msg = db.auth_user(user_id)
            AUTHORIZED_CHATS.add(user_id)
        else:
            AUTHORIZED_CHATS.add(user_id)
            with open('authorized_chats.txt', 'a') as file:
                file.write(f'{user_id}\n')
                msg = 'Authorization granted'
    sendMessage(msg, context.bot, update.message)

def unauthorize(update, context):
    reply_message = None
    message_ = None
    reply_message = update.message.reply_to_message
    message_ = update.message.text.split(' ')
    if len(message_) == 2:
        # Trying to unauthorize an user in private
        user_id = int(message_[1])
        if user_id in AUTHORIZED_CHATS:
            if DATABASE_URL is not None:
                db = DatabaseHelper()
                msg = db.unauth_user(user_id)
            else:
                msg = 'Authorization revoked'
            AUTHORIZED_CHATS.remove(user_id)
        else:
            msg = 'Already unauthorized'
    elif reply_message is None:
        # Trying to unauthorize a chat
        chat_id = update.effective_chat.id
        if chat_id in AUTHORIZED_CHATS:
            if DATABASE_URL is not None:
                db = DatabaseHelper()
                msg = db.unauth_user(chat_id)
            else:
                msg = 'Authorization revoked'
            AUTHORIZED_CHATS.remove(chat_id)
        else:
            msg = 'Already unauthorized'
    else:
        # Trying to unauthorize an user by replying
        user_id = reply_message.from_user.id
        if user_id in AUTHORIZED_CHATS:
            if DATABASE_URL is not None:
                db = DatabaseHelper()
                msg = db.unauth_user(user_id)
            else:
                msg = 'Authorization revoked'
            AUTHORIZED_CHATS.remove(user_id)
        else:
            msg = 'Already unauthorized'
    if DATABASE_URL is None:
        with open('authorized_chats.txt', 'a') as file:
            file.truncate(0)
            for i in AUTHORIZED_CHATS:
                file.write(f'{i}\n')
    sendMessage(msg, context.bot, update.message)

def auth_chats(update, context):
    users = ''
    for user in AUTHORIZED_CHATS:
        users += f"{user}\n"
    users = users if users != '' else "None"
    sendMessage(f'<b><u>Authorized Chats</u></b>\n<code>{users}</code>\n', context.bot, update.message)

authorize_handler = CommandHandler(BotCommands.AuthorizeCommand, authorize,
                                   filters=CustomFilters.owner_filter, run_async=True)
unauthorize_handler = CommandHandler(BotCommands.UnauthorizeCommand, unauthorize,
                                    filters=CustomFilters.owner_filter, run_async=True)
auth_handler = CommandHandler(BotCommands.UsersCommand, auth_chats,
                              filters=CustomFilters.owner_filter, run_async=True)
dispatcher.add_handler(authorize_handler)
dispatcher.add_handler(unauthorize_handler)
dispatcher.add_handler(auth_handler)
