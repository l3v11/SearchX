from telegram.ext import CommandHandler

from bot import dispatcher, BOOKMARKS, DATABASE_URL
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.database import DatabaseHelper

def addbookmark(update, context):
    args = update.message.text.split()
    drive_key = ''
    drive_id = ''
    if len(args) > 2:
        drive_key = args[1].strip()
        drive_id = args[2].strip()
    else:
        sendMessage("<b>Send a Drive Key and a Drive ID along with command</b>", context.bot, update.message)
        return
    if drive_key in BOOKMARKS:
        msg = 'Already added bookmark'
    elif DATABASE_URL is not None:
        msg = DatabaseHelper().add_bm(drive_key, drive_id)
        BOOKMARKS[drive_key] = drive_id
    else:
        BOOKMARKS[drive_key] = drive_id
        msg = 'Bookmark added'
    sendMessage(msg, context.bot, update.message)

def rembookmark(update, context):
    args = update.message.text.split()
    drive_key = ''
    if len(args) > 1:
        drive_key = args[1].strip()
    else:
        sendMessage("<b>Send a Drive Key along with command</b>", context.bot, update.message)
        return
    if drive_key in BOOKMARKS:
        if DATABASE_URL is not None:
            msg = DatabaseHelper().remove_bm(drive_key)
        else:
            msg = 'Bookmark removed'
        del BOOKMARKS[drive_key]
    else:
        msg = 'Already removed bookmark'
    sendMessage(msg, context.bot, update.message)

def bookmarks(update, context):
    drive_keys = ''
    if len(BOOKMARKS) == 0:
        drive_keys += 'None'
    else:
        drive_keys += '\n'.join(f'• <code>{drive_key}</code> - {BOOKMARKS[drive_key]}' for drive_key in BOOKMARKS)
    msg = f'<b><u>Bookmarks</u></b>\n{drive_keys}'
    sendMessage(msg, context.bot, update.message)

addbm_handler = CommandHandler(BotCommands.AddBookmarkCommand, addbookmark,
                               filters=CustomFilters.owner_filter)
rembm_handler = CommandHandler(BotCommands.RemBookmarkCommand, rembookmark,
                               filters=CustomFilters.owner_filter)
bookmarks_handler = CommandHandler(BotCommands.BookmarksCommand, bookmarks,
                                   filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(addbm_handler)
dispatcher.add_handler(rembm_handler)
dispatcher.add_handler(bookmarks_handler)
