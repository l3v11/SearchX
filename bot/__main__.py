import time

from psutil import cpu_percent, cpu_count, disk_usage, virtual_memory
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler

from bot import LOGGER, botStartTime, AUTHORIZED_CHATS, telegraph, dispatcher, updater
from bot.modules import auth, cancel, clone, count, delete, eval, list, permission, shell, status
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_builder import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendLogFile

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

def log(update, context):
    sendLogFile(context.bot, update.message)

help_string = '''
<b><a href='https://github.com/l3v11/SearchX'>SearchX</a></b> - The Ultimate Telegram Bot for Google Drive

Choose a help category:
'''

help_string_user = f'''
<u><b>User Commands</b></u>
<br><br>
• <b>/{BotCommands.StartCommand}</b>: Start the bot
<br><br>
• <b>/{BotCommands.ListCommand}</b> &lt;query&gt;: Search data on Drives
<br><br>
• <b>/{BotCommands.ListCommand} -d</b> &lt;query&gt;: Search folders on Drives
<br><br>
• <b>/{BotCommands.ListCommand} -f</b> &lt;query&gt;: Search files on Drives
<br><br>
• <b>/{BotCommands.CloneCommand}</b> &lt;url&gt;: Copy data from Drive / AppDrive / DriveApp / GDToT to Drive
<br><br>
• <b>/{BotCommands.CountCommand}</b> &lt;drive_url&gt;: Count data of Drive
<br><br>
• <b>/{BotCommands.CancelCommand}</b> &lt;gid&gt;: Cancel a task
<br><br>
• <b>/{BotCommands.StatusCommand}</b>: Get a status of all tasks
<br><br>
• <b>/{BotCommands.PingCommand}</b>: Ping the bot
<br><br>
• <b>/{BotCommands.StatsCommand}</b>: Get the system stats
<br><br>
• <b>/{BotCommands.HelpCommand}</b>: Get this message
'''

help_user = telegraph[0].create_page(
    title='SearchX Help',
    author_name='Levi',
    author_url='https://t.me/l3v11',
    html_content=help_string_user)['url']

help_string_admin = f'''
<u><b>Admin Commands</b></u>
<br><br>
• <b>/{BotCommands.PermissionCommand}</b> &lt;drive_url&gt; &lt;email&gt;: Set data permission of Drive (Email optional)
<br><br>
• <b>/{BotCommands.DeleteCommand}</b> &lt;drive_url&gt;: Delete data from Drive
<br><br>
• <b>/{BotCommands.AuthorizeCommand}</b>: Authorize an user or a chat for using the bot
<br><br>
• <b>/{BotCommands.UnauthorizeCommand}</b>: Unauthorize an user or a chat for using the bot
<br><br>
• <b>/{BotCommands.UsersCommand}</b>: View authorized chats
<br><br>
• <b>/{BotCommands.ShellCommand}</b> &lt;cmd&gt;: Run commands in terminal
<br><br>
• <b>/{BotCommands.ExecHelpCommand}</b>: Get help about executor
<br><br>
• <b>/{BotCommands.LogCommand}</b>: Get the log file
'''

help_admin = telegraph[0].create_page(
    title='SearchX Help',
    author_name='Levi',
    author_url='https://t.me/l3v11',
    html_content=help_string_admin)['url']

def bot_help(update, context):
    button = ButtonMaker()
    button.build_button("User", f"{help_user}")
    button.build_button("Admin", f"{help_admin}")
    sendMarkup(help_string, context.bot, update.message, InlineKeyboardMarkup(button.build_menu(2)))

def main():
    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand, stats,
                                   filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log,
                                 filters=CustomFilters.owner_filter, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand, bot_help,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    dispatcher.add_handler(help_handler)
    updater.start_polling()
    LOGGER.info("Bot started")
    updater.idle()

main()
