import time

from telegram.ext import CommandHandler

from bot import AUTHORIZED_CHATS, dispatcher, updater
from bot.modules import auth, clone, count, delete, list, permission, shell
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import *

def start(update, context):
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        if update.message.chat.type == "private":
            sendMessage("<b>Access granted</b>", context.bot, update)
        else:
            sendMessage("<b>I'm alive :)</b>", context.bot, update)
        LOGGER.info('Granted: {} [{}]'.format(update.message.from_user.first_name, update.message.from_user.id))
    else:
        sendMessage("<b>Access denied</b>", context.bot, update)
        LOGGER.info('Denied: {} [{}]'.format(update.message.from_user.first_name, update.message.from_user.id))

def ping(update, context):
    start_time = int(round(time.time() * 1000))
    reply = sendMessage("<b>Pong!</b>", context.bot, update)
    end_time = int(round(time.time() * 1000))
    editMessage(f'<code>{end_time - start_time}ms</code>', reply)

def bot_help(update, context):
    help_string = f'''
<u><i><b>Usage:</b></i></u>

For <i>folder</i> results only:
<code>/{BotCommands.ListCommand} -d &lt;query&gt;</code>

For <i>file</i> results only:
<code>/{BotCommands.ListCommand} -f &lt;query&gt;</code>

<u><i><b>Commands:</b></i></u>

/{BotCommands.StartCommand}: Start the bot

/{BotCommands.ListCommand} [query]: Search data on Drives

/{BotCommands.CloneCommand} [url]: Copy data from Drive / AppDrive / DriveApp / GDToT to Drive

/{BotCommands.CountCommand} [drive_url]: Count data of Drive

/{BotCommands.PermissionCommand} [drive_url] [email]: Set data permission of Drive (Email optional & Only owner)

/{BotCommands.DeleteCommand} [drive_url]: Delete data from Drive (Only owner)

/{BotCommands.AuthorizeCommand}: Authorize an user or a chat for using the bot (Only owner)

/{BotCommands.UnauthorizeCommand}: Unauthorize an user or a chat for using the bot (Only owner)

/{BotCommands.UsersCommand}: View authorized chats (Only owner)

/{BotCommands.ShellCommand} [cmd]: Execute bash commands (Only owner)

/{BotCommands.PingCommand}: Ping the bot

/{BotCommands.LogCommand}: Get the log file (Only owner)

/{BotCommands.HelpCommand}: Get this message
'''
    sendMessage(help_string, context.bot, update)

def log(update, context):
    sendLogFile(context.bot, update)

def main():
    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand, bot_help,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log,
                                 filters=CustomFilters.owner_filter, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling()
    LOGGER.info("Bot started")
    updater.idle()

main()
