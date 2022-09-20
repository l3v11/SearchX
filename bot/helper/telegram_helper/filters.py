from telegram import Message
from telegram.ext import MessageFilter

from bot import AUTHORIZED_USERS, OWNER_ID

class CustomFilters:

    class __OwnerFilter(MessageFilter):

        def filter(self, message: Message):
            return message.from_user.id == OWNER_ID

    owner_filter = __OwnerFilter()

    class __AuthorizedUserFilter(MessageFilter):

        def filter(self, message: Message):
            user_id = message.from_user.id
            return user_id in AUTHORIZED_USERS or user_id == OWNER_ID

    authorized_user = __AuthorizedUserFilter()

    class __AuthorizedChatFilter(MessageFilter):

        def filter(self, message: Message):
            return message.chat.id in AUTHORIZED_USERS

    authorized_chat = __AuthorizedChatFilter()
