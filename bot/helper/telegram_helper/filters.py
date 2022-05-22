from telegram import Message
from telegram.ext import MessageFilter

from bot import AUTHORIZED_CHATS, OWNER_ID

class CustomFilters:
    class __OwnerFilter(MessageFilter):
        def filter(self, message: Message):
            return bool(message.from_user.id == OWNER_ID)

    owner_filter = __OwnerFilter()

    class __AuthorizedUserFilter(MessageFilter):
        def filter(self, message: Message):
            id = message.from_user.id
            return bool(id in AUTHORIZED_CHATS or id == OWNER_ID)

    authorized_user = __AuthorizedUserFilter()

    class __AuthorizedChat(MessageFilter):
        def filter(self, message: Message):
            return bool(message.chat.id in AUTHORIZED_CHATS)

    authorized_chat = __AuthorizedChat()
