from telegram.ext import Filters

from bot import AUTHORIZED_CHATS, OWNER_ID

class CustomFilters:
    owner_filter = Filters.user(user_id=OWNER_ID)
    authorized_user = owner_filter | Filters.user(user_id=AUTHORIZED_CHATS)
    authorized_chat = owner_filter | Filters.chat(chat_id=AUTHORIZED_CHATS)
