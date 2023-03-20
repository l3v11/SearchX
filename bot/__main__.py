import os
import signal
import time

from psutil import cpu_percent, cpu_count, disk_usage, virtual_memory, net_io_counters
from sys import executable
from telegram.ext import CommandHandler

from bot import bot, LOGGER, botStartTime, TELEGRAPH, Interval, dispatcher, updater
from bot.modules import archive, auth, bookmark, cancel, clone, collage, count, delete, eval, frames, list, mediainfo, permission, shell, status
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from bot.helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_builder import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendLogFile

def start(update, context):
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        if update.message.chat.type == "private":
            sendMessage("<b>Access granted</b>", context.bot, update.message)
        else:
            sendMessage("<b>I'm alive :)</b>", context.bot, update.message)
    else:
        sendMessage("<b>Access denied</b>", context.bot, update.message)

def ping(update, context):
    start_time = int(round(time.time() * 1000))
    reply = sendMessage("<b>Pong!</b>", context.bot, update.message)
    end_time = int(round(time.time() * 1000))
    editMessage(f'<code>{end_time - start_time}ms</code>', reply)

def stats(update, context):
    total, used, free, disk = disk_usage('/')
    stats = '⚙️ <u><b>SYSTEM STATISTICS</b></u>' \
            f'\n\n<b>Total Disk Space:</b> {get_readable_file_size(total)}' \
            f'\n<b>Used:</b> {get_readable_file_size(used)} | <b>Free:</b> {get_readable_file_size(free)}' \
            f'\n\n<b>Upload:</b> {get_readable_file_size(net_io_counters().bytes_sent)}' \
            f'\n<b>Download:</b> {get_readable_file_size(net_io_counters().bytes_recv)}' \
            f'\n\n<b>Physical Cores:</b> {cpu_count(logical=False)}' \
            f'\n<b>Logical Cores:</b> {cpu_count(logical=True)}' \
            f'\n\n<b>CPU:</b> {cpu_percent(interval=0.5)}% | <b>RAM:</b> {virtual_memory().percent}%' \
            f'\n<b>DISK:</b> {disk}% | <b>Uptime:</b> {get_readable_time(time.time() - botStartTime)}'
    sendMessage(stats, context.bot, update.message)

def log(update, context):
    sendLogFile(context.bot, update.message)

def restart(update, context):
    restart_message = sendMessage("<b>Restart in progress...</b>", context.bot, update.message)
    if Interval:
        Interval[0].cancel()
        Interval.clear()
    clean_all()
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    os.execl(executable, executable, "-m", "bot")

help_string = '''
<b><a href='https://github.com/l3v11/SearchX'>SearchX</a></b> - The Ultimate Telegram Bot for Google Drive

Choose a help category:
'''

help_string_user = f'''
<b><u>User Commands</u></b>
<br><br>
• <b>/{BotCommands.StartCommand}</b>: Start the bot
<br><br>
• <b>/{BotCommands.ListCommand}</b> &lt;query&gt;: Search data in Google Drive
<br><br>
• <b>/{BotCommands.CloneCommand}</b> &lt;url&gt; &lt;drive_key&gt;: Clone data from Google Drive and GDToT (Drive Key optional)
<br><br>
• <b>/{BotCommands.CompressCommand}</b> &lt;url&gt;: Compress data from Google Drive and GDToT
<br><br>
• <b>/{BotCommands.ExtractCommand}</b> &lt;url&gt;: Extract data from Google Drive and GDToT
<br><br>
• <b>/{BotCommands.CountCommand}</b> &lt;drive_url&gt;: Count data from Google Drive
<br><br>
• <b>/{BotCommands.MediainfoCommand}</b> &lt;url&gt;: Generate mediainfo of a media file from Google Drive and URL
<br><br>
• <b>/{BotCommands.FramesCommand}</b> &lt;url&gt; &lt;count&gt;: Generate frames of a media file from Google Drive and URL (Count optional)
<br><br>
• <b>/{BotCommands.CollageCommand}</b> &lt;url&gt; &lt;grid&gt;: Generate collage of a media file from Google Drive and URL (Grid optional)
<br><br>
• <b>/{BotCommands.CancelCommand}</b> &lt;gid&gt;: Cancel a task
<br><br>
• <b>/{BotCommands.StatusCommand}</b>: Get status of all tasks
<br><br>
• <b>/{BotCommands.BookmarksCommand}</b>: Get the list of bookmarked destination drives
<br><br>
• <b>/{BotCommands.PingCommand}</b>: Ping the bot
<br><br>
• <b>/{BotCommands.StatsCommand}</b>: Get the system statistics
<br><br>
• <b>/{BotCommands.HelpCommand}</b>: Get help about the bot
'''

help_user = TELEGRAPH[0].create_page(
    title='SearchX Help',
    author_name='Levi',
    author_url='https://t.me/l3v11',
    html_content=help_string_user)['path']

help_string_admin = f'''
<b><u>Admin Commands</u></b>
<br><br>
• <b>/{BotCommands.PermissionCommand}</b> &lt;drive_url&gt; &lt;email&gt;: Set data permission in Google Drive (Email optional)
<br><br>
• <b>/{BotCommands.DeleteCommand}</b> &lt;drive_url&gt;: Delete data from Google Drive
<br><br>
• <b>/{BotCommands.AddBookmarkCommand}</b> &lt;drive_key&gt; &lt;drive_id&gt;: Add bookmark of a destination drive
<br><br>
• <b>/{BotCommands.RemBookmarkCommand}</b> &lt;drive_key&gt;: Remove bookmark of a destination drive
<br><br>
• <b>/{BotCommands.AuthorizeCommand}</b>: Grant authorization of an user
<br><br>
• <b>/{BotCommands.UnauthorizeCommand}</b>: Revoke authorization of an user
<br><br>
• <b>/{BotCommands.UsersCommand}</b>: Get the list of authorized users
<br><br>
• <b>/{BotCommands.ShellCommand}</b> &lt;cmd&gt;: Execute shell commands
<br><br>
• <b>/{BotCommands.EvalCommand}</b>: Evaluate Python expressions using eval() function
<br><br>
• <b>/{BotCommands.ExecCommand}</b>: Execute Python code using exec() function
<br><br>
• <b>/{BotCommands.ClearLocalsCommand}</b>: Clear the locals of eval() and exec() functions
<br><br>
• <b>/{BotCommands.LogCommand}</b>: Get the log file
<br><br>
• <b>/{BotCommands.RestartCommand}</b>: Restart the bot
'''

help_admin = TELEGRAPH[0].create_page(
    title='SearchX Help',
    author_name='Levi',
    author_url='https://t.me/l3v11',
    html_content=help_string_admin)['path']

def bot_help(update, context):
    button = ButtonMaker()
    button.build_button("User", f"https://graph.org/{help_user}")
    button.build_button("Admin", f"https://graph.org/{help_admin}")
    sendMessage(help_string, context.bot, update.message, button.build_menu(2))

def main():
    start_cleanup()
    if os.path.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        try:
            bot.editMessageText("<b>Restarted successfully</b>", chat_id, msg_id)
        except:
            pass
        os.remove(".restartmsg")

    start_handler = CommandHandler(BotCommands.StartCommand, start)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
    stats_handler = CommandHandler(BotCommands.StatsCommand, stats,
                                   filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
    log_handler = CommandHandler(BotCommands.LogCommand, log,
                                 filters=CustomFilters.owner_filter)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                     filters=CustomFilters.owner_filter)
    help_handler = CommandHandler(BotCommands.HelpCommand, bot_help,
                                  filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    updater.start_polling()
    LOGGER.info("Bot started")
    signal.signal(signal.SIGINT, exit_clean_up)

main()
