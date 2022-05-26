from telegram.ext import CommandHandler

from bot import MY_BOOKMARKS, DATABASE_URL, dispatcher
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.ext_utils.database import DatabaseHelper

def add_bookmark(update, context):
    if DATABASE_URL is not None:
        try:
            query = update.message.text.split(' ', maxsplit=1)[1]
            bm_name = query.split(' ', maxsplit=1)[0]
            bm_id = query.split(' ', maxsplit=1)[1]
        except IndexError:
            sendMessage('Usage: /addbm &lt;name&gt; &lt;id&gt;', context.bot, update.message)
            return
        reply = sendMessage('<code>Adding Bookmark...</code>', context.bot, update.message)
        if bm_name in MY_BOOKMARKS.keys():
            msg = f'<b>Bookmark already exists</b>\n\n<b>Name:</b> <code>{bm_name}</code>\n<b>ID:</b> <code>{MY_BOOKMARKS[bm_name]}</code>'
        elif bm_id in MY_BOOKMARKS.values():
            msg = f'<b>Bookmark already exists</b>\n\n<b>Name:</b> <code>{[key for key in MY_BOOKMARKS if MY_BOOKMARKS[key]==bm_id][0]}</code>\n<b>ID:</b> <code>{bm_id}</code>'
        else:
            MY_BOOKMARKS[bm_name] = bm_id
            db = DatabaseHelper()
            db.add_bm(bm_name, bm_id)
            msg = f'<b>Bookmark Added</b>\n\n<b>Name:</b> <code>{bm_name}</code>\n<b>ID:</b> <code>{bm_id}</code>'
        editMessage(msg, reply)
    else:
        sendMessage('<b>Database URL not set</b>', context.bot, update.message)

def rm_bookmark(update, context):
    if DATABASE_URL is not None:
        try:
            bm_name = update.message.text.split(' ', maxsplit=1)[1]
        except IndexError:
            sendMessage('Usage: /rmbm &lt;name&gt;', context.bot, update.message)
            return
        reply = sendMessage('<code>Removing Bookmark...</code>', context.bot, update.message)
        if bm_name not in MY_BOOKMARKS.keys():
            msg = f'<b>Bookmark does not exist</b>\n\n<b>Name:</b> <code>{bm_name}</code>'
        else:
            del MY_BOOKMARKS[bm_name]
            db = DatabaseHelper()
            db.rm_bm(bm_name)
            msg = f'<b>Bookmark Removed</b>\n\n<b>Name:</b> <code>{bm_name}</code>'
        editMessage(msg, reply)
    else:
        sendMessage('<b>Database URL not set</b>', context.bot, update.message)

def list_bookmarks(update, context):
    if DATABASE_URL is not None:
        reply = sendMessage('<b>Fetching Bookmarks...</b>', context.bot, update.message)
        db = DatabaseHelper()
        bm_dict = db.get_bms()
        bm_string = ''
        for bm in bm_dict:
            bm_string += f'<code>{bm}</code> - <code>{bm_dict[bm]}</code>\n'
        if len(bm_dict) == 0:
            bm_string = '<code>No Bookmarks</code>'
        editMessage(f'<b><u>Bookmarks</u></b>\n\n{bm_string}', reply)
    else:
        sendMessage('<b>Database URL not set</b>', context.bot, update.message)

addbm_handler = CommandHandler(BotCommands.AddBmCommand, add_bookmark, filters=CustomFilters.authorized_user, run_async=True)
rmbm_handler = CommandHandler(BotCommands.RmBmCommand, rm_bookmark, filters=CustomFilters.authorized_user, run_async=True)
listbm_handler = CommandHandler(BotCommands.ListBmCommand, list_bookmarks, filters=CustomFilters.authorized_user, run_async=True)

dispatcher.add_handler(addbm_handler)
dispatcher.add_handler(rmbm_handler)
dispatcher.add_handler(listbm_handler)
