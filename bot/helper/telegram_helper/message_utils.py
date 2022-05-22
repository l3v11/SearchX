from telegram import InlineKeyboardMarkup
from telegram.message import Message

from bot import bot, LOGGER, Interval, STATUS_UPDATE_INTERVAL, \
    status_reply_dict, status_reply_dict_lock
from bot.helper.ext_utils.bot_utils import SetInterval, get_readable_message

def sendMessage(text: str, bot, message: Message):
    try:
        return bot.sendMessage(message.chat_id,
                                reply_to_message_id=message.message_id,
                                text=text, parse_mode='HTMl',
                                disable_web_page_preview=True)
    except Exception as e:
        LOGGER.error(str(e))

def sendMarkup(text: str, bot, message: Message, reply_markup: InlineKeyboardMarkup):
    try:
        return bot.sendMessage(message.chat_id,
                                reply_to_message_id=message.message_id,
                                text=text, reply_markup=reply_markup,
                                parse_mode='HTMl', disable_web_page_preview=True)
    except Exception as e:
        LOGGER.error(str(e))

def editMessage(text: str, message: Message, reply_markup=None):
    try:
        bot.editMessageText(text=text, message_id=message.message_id,
                              chat_id=message.chat.id,
                              reply_markup=reply_markup, parse_mode='HTMl',
                              disable_web_page_preview=True)
    except Exception as e:
        LOGGER.error(str(e))

def deleteMessage(bot, message: Message):
    try:
        bot.deleteMessage(chat_id=message.chat.id,
                           message_id=message.message_id)
    except Exception as e:
        LOGGER.error(str(e))

def sendLogFile(bot, message: Message):
    with open('log.txt', 'rb') as f:
        bot.sendDocument(document=f, filename=f.name,
                          reply_to_message_id=message.message_id,
                          chat_id=message.chat_id)

def delete_all_messages():
    with status_reply_dict_lock:
        for message in list(status_reply_dict.values()):
            try:
                deleteMessage(bot, message)
                del status_reply_dict[message.chat.id]
            except Exception as e:
                LOGGER.error(str(e))

def update_all_messages():
    msg = get_readable_message()
    with status_reply_dict_lock:
        for chat_id in list(status_reply_dict.keys()):
            if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id].text:
                editMessage(msg, status_reply_dict[chat_id])
                status_reply_dict[chat_id].text = msg

def sendStatusMessage(msg, bot):
    if len(Interval) == 0:
        Interval.append(SetInterval(STATUS_UPDATE_INTERVAL, update_all_messages))
    progress = get_readable_message()
    with status_reply_dict_lock:
        if msg.chat.id in list(status_reply_dict.keys()):
            try:
                message = status_reply_dict[msg.chat.id]
                deleteMessage(bot, message)
                del status_reply_dict[msg.chat.id]
            except Exception as e:
                LOGGER.error(str(e))
                del status_reply_dict[msg.chat.id]
        message = sendMessage(progress, bot, msg)
        status_reply_dict[msg.chat.id] = message
