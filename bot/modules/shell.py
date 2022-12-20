import subprocess

from telegram.ext import CommandHandler

from bot import dispatcher
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters

def shell(update, context):
    message = update.effective_message
    cmd = message.text.split(maxsplit=1)
    if len(cmd) == 1:
        return message.reply_text('<b>Send a command to execute</b>', parse_mode='HTML')
    cmd = cmd[1]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    reply = ''
    stdout = stdout.decode()
    stderr = stderr.decode()
    if len(stdout) != 0:
        reply += f"<b>Stdout</b>\n<code>{stdout}</code>\n"
    if len(stderr) != 0:
        reply += f"<b>Stderr</b>\n<code>{stderr}</code>\n"
    if len(reply) > 3000:
        with open('output.txt', 'w') as file:
            file.write(reply)
        with open('output.txt', 'rb') as doc:
            context.bot.send_document(
                document=doc,
                filename=doc.name,
                chat_id=message.chat_id,
                reply_to_message_id=message.message_id)
    elif len(reply) != 0:
        message.reply_text(reply, parse_mode='HTML')
    else:
        message.reply_text('<b>Command executed</b>', parse_mode='HTML')

shell_handler = CommandHandler(BotCommands.ShellCommand, shell,
                               filters=CustomFilters.owner_filter)
dispatcher.add_handler(shell_handler)
