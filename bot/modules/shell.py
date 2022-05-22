import subprocess

from telegram.ext import CommandHandler

from bot import dispatcher
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage

def shell(update, context):
    message = update.effective_message
    cmd = message.text.split(' ', 1)
    if len(cmd) == 1:
        return sendMessage('<b>Send a command to execute</b>', context.bot, update.message)
    cmd = cmd[1]
    process = subprocess.run(cmd, capture_output=True, shell=True)
    reply = ''
    stderr = process.stderr.decode('utf-8')
    stdout = process.stdout.decode('utf-8')
    if len(stdout) != 0:
        reply += f"<b>Stdout</b>\n<code>{stdout}</code>\n"
    if len(stderr) != 0:
        reply += f"<b>Stderr</b>\n<code>{stderr}</code>\n"
    if len(reply) > 3000:
        with open('shell_output.txt', 'w') as file:
            file.write(reply)
        with open('shell_output.txt', 'rb') as doc:
            context.bot.send_document(
                document=doc,
                filename=doc.name,
                reply_to_message_id=message.message_id,
                chat_id=message.chat_id)
    elif len(reply) != 0:
        sendMessage(reply, context.bot, update.message)
    else:
        sendMessage('Executed', context.bot, update.message)

shell_handler = CommandHandler(BotCommands.ShellCommand, shell,
                               filters=CustomFilters.owner_filter, run_async=True)
dispatcher.add_handler(shell_handler)
