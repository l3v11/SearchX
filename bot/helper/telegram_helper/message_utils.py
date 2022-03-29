from telegram.message import Message
from telegram.update import Update

from bot import LOGGER, bot

def sendMessage(text: str, bot, update: Update):
    try:
        return bot.send_message(update.message.chat_id,
                                reply_to_message_id=update.message.message_id,
                                text=text, parse_mode='HTMl',
                                disable_web_page_preview=True)
    except Exception as e:
        LOGGER.error(str(e))

def editMessage(text: str, message: Message, reply_markup=None):
    try:
        bot.edit_message_text(chat_id=message.chat.id,
                              message_id=message.message_id,
                              reply_markup=reply_markup,
                              text=text, parse_mode='HTMl',
                              disable_web_page_preview=True)
    except Exception:
        pass

def deleteMessage(bot, message: Message):
    try:
        bot.delete_message(chat_id=message.chat.id,
                           message_id=message.message_id)
    except Exception as e:
        LOGGER.error(str(e))

def sendLogFile(bot, update: Update):
    with open('log.txt', 'rb') as f:
        bot.send_document(document=f, filename=f.name,
                          reply_to_message_id=update.message.message_id,
                          chat_id=update.message.chat_id)
