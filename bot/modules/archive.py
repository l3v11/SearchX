import os
import re
import requests
import subprocess
import threading

from html import escape
from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher, DOWNLOAD_DIR, Interval, INDEX_URL, download_dict, download_dict_lock, status_reply_dict_lock
from bot.helper.download_utils.ddl_generator import gdtot
from bot.helper.download_utils.gd_downloader import add_gd_download
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import is_gdrive_link, is_gdtot_link
from bot.helper.ext_utils.exceptions import ArchiveExceptionHandler, DDLExceptionHandler
from bot.helper.ext_utils.fs_utils import clean_download, clean_target, get_base_name, get_path_size
from bot.helper.status_utils.compress_status import CompressStatus
from bot.helper.status_utils.extract_status import ExtractStatus
from bot.helper.status_utils.upload_status import UploadStatus
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, delete_all_messages, update_all_messages

class ArchiveListener:
    def __init__(self, bot, message, is_compress=False, is_extract=False, pswd=None):
        self.bot = bot
        self.message = message
        self.uid = message.message_id
        self.is_compress = is_compress
        self.is_extract = is_extract
        self.pswd = pswd
        self.dir = f'{DOWNLOAD_DIR}{self.uid}'
        self.suproc = None

    def clean(self):
        try:
            with status_reply_dict_lock:
                Interval[0].cancel()
                Interval.clear()
            delete_all_messages()
        except:
            pass

    def onDownloadComplete(self):
        with download_dict_lock:
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
        if name == 'None' or not os.path.exists(f'{self.dir}/{name}'):
            name = os.listdir(self.dir)[-1]
        m_path = f"{self.dir}/{name}"
        size = get_path_size(m_path)
        if self.is_compress:
            path = f"{m_path}.zip"
            with download_dict_lock:
                download_dict[self.uid] = CompressStatus(name, size, gid, self)
            LOGGER.info(f"Compressing: {name}")
            if self.pswd is not None:
                self.suproc = subprocess.Popen(["7z", "a", "-mx=0", f"-p{self.pswd}", path, m_path])
            else:
                self.suproc = subprocess.Popen(["7z", "a", "-mx=0", path, m_path])
            self.suproc.wait()
            if self.suproc.returncode == -9:
                return
            clean_target(m_path)
        elif self.is_extract:
            try:
                if os.path.isfile(m_path):
                    path = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(name, size, gid, self)
                if os.path.isdir(m_path):
                    path = m_path
                    for dirpath, subdir, files in os.walk(m_path, topdown=False):
                        for file_ in files:
                            if re.search(r'\.part0*1\.rar$|\.7z\.0*1$|\.zip\.0*1$|\.zip$|\.7z$|^.(?!.*\.part\d+\.rar)(?=.*\.rar$)', file_):
                                f_path = os.path.join(dirpath, file_)
                                if self.pswd is not None:
                                    self.suproc = subprocess.Popen(["7z", "x", f"-p{self.pswd}", f_path, f"-o{dirpath}", "-aot"])
                                else:
                                    self.suproc = subprocess.Popen(["7z", "x", f_path, f"-o{dirpath}", "-aot"])
                                self.suproc.wait()
                                if self.suproc.returncode == -9:
                                    return
                                elif self.suproc.returncode != 0:
                                    LOGGER.error("Failed to extract the split archive")
                        if self.suproc is not None and self.suproc.returncode == 0:
                            for file_ in files:
                                if re.search(r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$|\.zip$|\.rar$|\.7z$', file_):
                                    del_path = os.path.join(dirpath, file_)
                                    try:
                                        os.remove(del_path)
                                    except:
                                        return
                else:
                    if self.pswd is not None:
                        self.suproc = subprocess.Popen(["7z", "x", f"-p{self.pswd}", m_path, f"-o{path}", "-aot"])
                    else:
                        self.suproc = subprocess.Popen(["7z", "x", m_path, f"-o{path}", "-aot"])
                    self.suproc.wait()
                    if self.suproc.returncode == -9:
                        return
                    elif self.suproc.returncode == 0:
                        try:
                            os.remove(m_path)
                        except:
                            return
                    else:
                        LOGGER.error("Failed to extract the archive")
                        path = m_path
            except ArchiveExceptionHandler as err:
                LOGGER.error(err)
                path = m_path
        else:
            path = m_path
        up_dir, up_name = path.rsplit('/', 1)
        up_path = f'{up_dir}/{up_name}'
        size = get_path_size(up_path)
        LOGGER.info(f"Uploading: {up_name}")
        drive = GoogleDriveHelper(up_name, up_dir, size, self)
        upload_status = UploadStatus(drive, size, gid, self)
        with download_dict_lock:
            download_dict[self.uid] = upload_status
        update_all_messages()
        drive.upload(up_name)

    def onUploadComplete(self, link: str, size, files, folders, typ, name):
        msg = f'<b>Name:</b> <code>{escape(name)}</code>'
        msg += f'\n<b>Size:</b> {size}'
        msg += f'\n<b>Type:</b> {typ}'
        if typ == "Folder":
            msg += f'\n<b>SubFolders:</b> {folders}'
            msg += f'\n<b>Files:</b> {files}'
        msg += f'\n\n<b><a href="{link}">Drive Link</a></b>'
        if INDEX_URL is not None:
            url_path = requests.utils.quote(f'{name}')
            url = f'{INDEX_URL}/{url_path}'
            if typ == "Folder":
                url += '/'
                msg += f'<b> | <a href="{url}">Index Link</a></b>'
            else:
                msg += f'<b> | <a href="{url}">Index Link</a></b>'
        sendMessage(msg, self.bot, self.message)
        clean_download(self.dir)
        with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

    def onDownloadError(self, error):
        error = error.replace('<', '').replace('>', '')
        clean_download(self.dir)
        with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        sendMessage(error, self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

    def onUploadError(self, error):
        error = error.replace('<', '').replace('>', '')
        clean_download(self.dir)
        with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        sendMessage(error, self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

def _archive(bot, message, is_compress=False, is_extract=False):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)
    is_gdtot = False
    link = ''
    if len(message_args) > 1:
        link = message_args[1].strip()
        if link.startswith(('|', 'pswd:')):
            link = ''
    name = mesg[0].split('|', maxsplit=1)
    if len(name) > 1:
        if 'pswd:' in name[0]:
            name = ''
        else:
            name = name[1].split('pswd:')[0].strip()
    else:
        name = ''
    pswd = mesg[0].split(' pswd: ')
    pswd = pswd[1] if len(pswd) > 1 else None
    if link != '':
        link = re.split(r'pswd:|\|', link)[0]
        link = link.strip()
    reply_to = message.reply_to_message
    if reply_to is not None:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    is_gdtot = is_gdtot_link(link)
    if is_gdtot:
        msg = sendMessage(f"<b>Processing:</b> <code>{link}</code>", bot, message)
        LOGGER.info(f"Processing: {link}")
        try:
            link = gdtot(link)
            deleteMessage(bot, msg)
        except DDLExceptionHandler as err:
            deleteMessage(bot, msg)
            LOGGER.error(err)
            return sendMessage(str(err), bot, message)
    listener = ArchiveListener(bot, message, is_compress, is_extract, pswd)
    if is_gdrive_link(link):
        threading.Thread(target=add_gd_download, args=(link, f'{DOWNLOAD_DIR}{listener.uid}', listener, name, is_gdtot)).start()
    else:
        help_msg = '<b><u>Instructions</u></b>\nSend a link along with command'
        help_msg += '\n\n<b><u>Supported Sites</u></b>\n• Google Drive\n• GDToT'
        help_msg += '\n\n<b><u>Set Custom Name</u></b>\nAdd "<code>|customname</code>" after the link'
        help_msg += '\n\n<b><u>Set Password</u></b>\nAdd "<code>pswd: xxx</code>" after the link'
        sendMessage(help_msg, bot, message)


def compress_data(update, context):
    _archive(context.bot, update.message, is_compress=True)

def extract_data(update, context):
    _archive(context.bot, update.message, is_extract=True)

compress_handler = CommandHandler(BotCommands.CompressCommand, compress_data,
                                  filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
extract_handler = CommandHandler(BotCommands.ExtractCommand, extract_data,
                                 filters=CustomFilters.authorized_user | CustomFilters.authorized_chat)
dispatcher.add_handler(compress_handler)
dispatcher.add_handler(extract_handler)
