import time

from psutil import cpu_percent, cpu_count, disk_usage, virtual_memory
from telegram.ext import CommandHandler

from bot import LOGGER, botStartTime, AUTHORIZED_CHATS, dispatcher, updater
from bot.modules import auth, cancel, clone, count, delete, eval, list, permission, shell, status
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import *

def start(update, context):
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        if update.message.chat.type == "private":
            sendMessage("<b>Access granted</b>", context.bot, update.message)
        else:
            sendMessage("<b>I'm alive :)</b>", context.bot, update.message)
        LOGGER.info('Granted: {} [{}]'.format(update.message.from_user.first_name, update.message.from_user.id))
    else:
        sendMessage("<b>Access denied</b>", context.bot, update.message)
        LOGGER.info('Denied: {} [{}]'.format(update.message.from_user.first_name, update.message.from_user.id))

def ping(update, context):
    start_time = int(round(time.time() * 1000))
    reply = sendMessage("<b>Pong!</b>", context.bot, update.message)
    end_time = int(round(time.time() * 1000))
    editMessage(f'<code>{end_time - start_time}ms</code>', reply)

def stats(update, context):
    uptime = get_readable_time(time.time() - botStartTime)
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    cpu = cpu_percent(interval=0.5)
    ram = virtual_memory().percent
    p_core = cpu_count(logical=False)
    t_core = cpu_count(logical=True)
    stats = "⚙️ <u><b>SYSTEM STATISTICS</b></u>" \
            f"\n\n<b>Total Disk Space:</b> {total}" \
            f"\n<b>Used:</b> {used} | <b>Free:</b> {free}" \
            f"\n\n<b>Physical Cores:</b> {p_core} | <b>Total Cores:</b> {t_core}" \
            f"\n\n<b>CPU:</b> {cpu}% | <b>RAM:</b> {ram}%" \
            f"\n<b>DISK:</b> {disk}% | <b>Uptime:</b> {uptime}"
    sendMessage(stats, context.bot, update.message)

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

/{BotCommands.CancelCommand} [gid]: Cancel a task

/{BotCommands.StatusCommand}: Get a status of all tasks

/{BotCommands.PermissionCommand} [drive_url] [email]: Set data permission of Drive (Email optional & Only owner)

/{BotCommands.DeleteCommand} [drive_url]: Delete data from Drive (Only owner)

/{BotCommands.AuthorizeCommand}: Authorize an user or a chat for using the bot (Only owner)

/{BotCommands.UnauthorizeCommand}: Unauthorize an user or a chat for using the bot (Only owner)

/{BotCommands.UsersCommand}: View authorized chats (Only owner)

/{BotCommands.ShellCommand} [cmd]: Run commands in terminal (Only owner)

/{BotCommands.ExecHelpCommand}: Get help for executor (Only owner)

/{BotCommands.PingCommand}: Ping the bot

/{BotCommands.StatsCommand}: Get the system stats

/{BotCommands.LogCommand}: Get the log file (Only owner)

/{BotCommands.HelpCommand}: Get this message
'''
    sendMessage(help_string, context.bot, update.message)

def log(update, context):
    sendLogFile(context.bot, update.message)

def main():
    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand, stats,
                                   filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand, bot_help,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log,
                                 filters=CustomFilters.owner_filter, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling()
    LOGGER.info("Bot started")
    updater.idle()

main()
