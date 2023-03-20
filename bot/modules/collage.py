import datetime
import mimetypes
import os
import random
import requests
import string
import subprocess

from PIL import Image, ImageFont, ImageDraw, ImageOps
from telegram.ext import CommandHandler
from urllib.parse import unquote_plus

from bot import LOGGER, DOWNLOAD_DIR, dispatcher
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import new_thread, get_readable_file_size, slowpics_collection, is_url, is_gdrive_link
from bot.helper.ext_utils.exceptions import DDLExceptionHandler
from bot.helper.ext_utils.fs_utils import clean_download
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_builder import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters

@new_thread
def collageNode(update, context):
    args = update.message.text.split()
    reply_to = update.message.reply_to_message
    link = ''
    grid = ''
    row = 4
    col = 4
    if len(args) > 1:
        link = args[1].strip()
        try:
            grid = args[2].split("x", maxsplit=1)
            row = int(grid[0])
            col = int(grid[1])
        except (IndexError, ValueError):
            pass
    if reply_to:
        link = reply_to.text.split(maxsplit=1)[0].strip()
        try:
            grid = args[1].split("x", maxsplit=1)
            row = int(grid[0])
            col = int(grid[1])
        except (IndexError, ValueError):
            pass
    if row > 5 or col > 5:
        row = 5
        col = 5
    elif row != col:
        row = 4
        col = 4
    if is_url(link):
        msg = sendMessage(f"<b>Getting {row}x{col} collage:</b> <code>{link}</code>", context.bot, update.message)
        LOGGER.info(f"Getting {row}x{col} collage: {link}")
        if is_gdrive_link(link):
            try:
                gd = GoogleDriveHelper()
                res, file_id, access_token, name, size, mime_type = gd.fileinfo(link)
                if res != "":
                    deleteMessage(context.bot, msg)
                    return sendMessage(res, context.bot, update.message)
                if mime_type == "application/vnd.google-apps.folder":
                    raise DDLExceptionHandler("Folder is not supported")
                file_dl = f"https://www.googleapis.com/drive/v3/files/{file_id}\?supportsAllDrives\=true\&alt\=media"
                header = f"Authorization: Bearer {access_token}"
                out = subprocess.run(f"ffprobe -headers '{header}' -i {file_dl} -show_entries format=duration -v error -of csv=p=0", capture_output=True, shell=True)
                stderr = out.stderr.decode('utf-8')
                if "403 Forbidden" in stderr:
                    raise DDLExceptionHandler("Download quota exceeded")
                duration = out.stdout.decode('utf-8')
                if duration == '':
                    raise ValueError("Unsupported media file")
                durationhms = str(datetime.timedelta(seconds=int(float(duration))))
                uid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
                path = f"{DOWNLOAD_DIR}{uid}"
                os.makedirs(path)
                for seconds in random.sample(range(int(float(duration))), int(row*col)):
                    img = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=3))
                    genss = subprocess.run(f"ffmpeg -headers '{header}' -hide_banner -ss {seconds} -i {file_dl} -frames:v 1 -q:v 2 -y {path}/{img}.png", capture_output=True, shell=True)
                    if "403 Forbidden" in genss.stderr.decode('utf-8'):
                        raise DDLExceptionHandler("Download quota exceeded fucker")
                img_list = os.listdir(path)
                images = [Image.open(fp) for fp in [os.path.join(path, file) for file in img_list]]
                widths, heights = zip(*(i.size for i in images))
                max_width = max(widths)
                max_height = max(heights)
                canvas_width = max_width*row
                canvas_height = max_height*col
                canvas = Image.new(mode="RGB", size=(canvas_width, canvas_height), color=(0, 0, 0))
                tile_count=0
                for j in range(0, canvas_height - 1, max_height):
                    for i in range(0, canvas_width - 1, max_width):
                        im = Image.open(f'{path}/{img_list[tile_count]}')
                        canvas.paste(im, box=(i, j))
                        tile_count+=1
                canvas_exp = ImageOps.expand(canvas, border=(0,int(canvas_height/6.5),0,0), fill=(0, 0, 0))
                draw = ImageDraw.Draw(canvas_exp)
                text = f"{name}\nSize: {size}\nDuration: {durationhms}\nDimension: {max_width}x{max_height}"
                font = ImageFont.truetype(font="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=int(canvas_height/30))
                draw.text((30,10), text=text, fill=(255, 255, 255), font=font)
                collage_path = f"{path}/collage"
                os.makedirs(collage_path)
                img = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=4))
                canvas_res = canvas_exp.resize(size=(max_width, max_height))
                canvas_res.save(f"{collage_path}/{img}.png")
                img_link = slowpics_collection(collage_path)
                LOGGER.info(f"img limk {img_link}")
                result = ""
                result += f"<b>Name:</b> <code>{name}</code>"
                result += f"\n<b>Size:</b> <code>{size}</code>"
                result += f"\n<b>Type:</b> <code>{mime_type}</code>"
                button = ButtonMaker()
                button.build_button("VIEW COLLAGE 🗂️", f"{img_link}")
                clean_download(path)
                deleteMessage(context.bot, msg)
                sendMessage(result, context.bot, update.message, button.build_menu(1))
            except Exception as err:
                deleteMessage(context.bot, msg)
                LOGGER.error(str(err))
                return sendMessage(str(err), context.bot, update.message)
        else:
            try:
                res = requests.head(link, stream=True)
                name = unquote_plus(link).rsplit('/', 1)[-1]
                size = get_readable_file_size(int(res.headers["Content-Length"].strip()))
                mime_type = res.headers.get("Content-Type", mimetypes.guess_type(name)).rsplit(";", 1)[0]
                out = subprocess.run(["ffprobe", "-i", f"{link}", "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"], capture_output=True)
                duration = out.stdout.decode('utf-8')
                if duration == '':
                    raise ValueError("Unsupported media file")
                durationhms = str(datetime.timedelta(seconds=int(float(duration))))
                uid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
                path = f"{DOWNLOAD_DIR}{uid}"
                os.makedirs(path)
                sscount=1
                for seconds in random.sample(range(int(float(duration))), int(row*col)):
                    img = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=4))
                    genss = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{seconds}", "-i", f"{link}", "-frames:v", "1", "-q:v", "2", "-y", f"{path}/{img}.png"], capture_output=True)
                    sscount+=1
                img_list = os.listdir(path)
                images = [Image.open(fp) for fp in [os.path.join(path, file) for file in img_list]]
                widths, heights = zip(*(i.size for i in images))
                max_width = max(widths)
                max_height = max(heights)
                canvas_width = max_width*row
                canvas_height = max_height*col
                canvas = Image.new(mode="RGB", size=(canvas_width, canvas_height), color=(0, 0, 0))
                tile_count=0
                for j in range(0, canvas_height - 1, max_height):
                    for i in range(0, canvas_width - 1, max_width):
                        im = Image.open(f'{path}/{img_list[tile_count]}')
                        canvas.paste(im, box=(i, j))
                        tile_count+=1
                canvas_exp = ImageOps.expand(canvas, border=(0,int(canvas_height/6.5),0,0), fill=(0, 0, 0))
                draw = ImageDraw.Draw(canvas_exp)
                text = f"{name}\nSize: {size}\nDuration: {durationhms}\nDimension: {max_width}x{max_height}"
                font = ImageFont.truetype(font="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=int(canvas_height/30))
                draw.text((30,10), text=text, fill=(255, 255, 255), font=font)
                collage_path = f"{path}/collage"
                os.makedirs(collage_path)
                img = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=4))
                canvas_res = canvas_exp.resize(size=(max_width, max_height))
                canvas_res.save(f"{collage_path}/{img}.png")
                img_link = slowpics_collection(collage_path)
                result = ""
                result += f"<b>Name:</b> <code>{name}</code>"
                result += f"\n<b>Size:</b> <code>{size}</code>"
                result += f"\n<b>Type:</b> <code>{mime_type}</code>"
                button = ButtonMaker()
                button.build_button("VIEW COLLAGE 🗂️", f"{img_link}")
                clean_download(path)
                deleteMessage(context.bot, msg)
                sendMessage(result, context.bot, update.message, button.build_menu(1))
            except KeyError:
                deleteMessage(context.bot, msg)
                err = "Invalid link"
                LOGGER.error(str(err))
                return sendMessage(str(err), context.bot, update.message)
            except Exception as err:
                deleteMessage(context.bot, msg)
                LOGGER.error(str(err))
                return sendMessage(str(err), context.bot, update.message)
    else:
        sendMessage("<b>Send a link along with command</b>", context.bot, update.message)

collage_handler = CommandHandler(BotCommands.CollageCommand, collageNode,
                                 filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(collage_handler)
