import os
import re
import requests
import shutil
import subprocess
import threading

from html import escape
from pathlib import PurePath
from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher, DOWNLOAD_DIR, Interval, INDEX_URL, download_dict, download_dict_lock
from bot.helper.download_utils.ddl_generator import appdrive, gdtot
from bot.helper.download_utils.gd_downloader import add_gd_download
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import is_gdrive_link, is_appdrive_link, is_gdtot_link
from bot.helper.ext_utils.exceptions import CompressExceptionHandler, DDLExceptionHandler
from bot.helper.ext_utils.fs_utils import clean_download, get_base_name, get_path_size
from bot.helper.status_utils.archive_status import ArchiveStatus
from bot.helper.status_utils.extract_status import ExtractStatus
from bot.helper.status_utils.upload_status import UploadStatus
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, delete_all_messages, update_all_messages

class CompressListener:
    def __init__(self, bot, message, is_archive=False, is_extract=False, pswd=None):
        self.bot = bot
        self.message = message
        self.uid = self.message.message_id
        self.is_archive = is_archive
        self.is_extract = is_extract
        self.pswd = pswd

    def clean(self):
        try:
            Interval[0].cancel()
            del Interval[0]
            delete_all_messages()
        except IndexError:
            pass

    def onDownloadComplete(self):
        with download_dict_lock:
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
            size = download.size_raw()
            m_path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
        if self.is_archive:
            try:
                with download_dict_lock:
                    download_dict[self.uid] = ArchiveStatus(name, m_path, size)
                path = m_path + ".zip"
                LOGGER.info(f"Archiving: {name}")
                if self.pswd is not None:
                    subprocess.run(["7z", "a", "-mx=0", f"-p{self.pswd}", path, m_path])
                else:
                    subprocess.run(["7z", "a", "-mx=0", path, m_path])
            except FileNotFoundError:
                LOGGER.info("File to archive not found")
                self.onUploadError('Internal error')
                return
            try:
                shutil.rmtree(m_path)
            except:
                os.remove(m_path)
        elif self.is_extract:
            try:
                if os.path.isfile(m_path):
                    path = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(name, m_path, size)
                if os.path.isdir(m_path):
                    for dirpath, subdir, files in os.walk(m_path, topdown=False):
                        for file_ in files:
                            if file_.endswith((".zip", ".7z")) or re.search(r'\.part0*1\.rar$|\.7z\.0*1$|\.zip\.0*1$', file_) \
                               or (file_.endswith(".rar") and not re.search(r'\.part\d+\.rar$', file_)):
                                m_path = os.path.join(dirpath, file_)
                                if self.pswd is not None:
                                    result = subprocess.run(["7z", "x", f"-p{self.pswd}", m_path, f"-o{dirpath}", "-aot"])
                                else:
                                    result = subprocess.run(["7z", "x", m_path, f"-o{dirpath}", "-aot"])
                                if result.returncode != 0:
                                    LOGGER.error("Failed to extract the archive")
                        for file_ in files:
                            if file_.endswith((".rar", ".zip", ".7z")) or re.search(r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$', file_):
                                del_path = os.path.join(dirpath, file_)
                                os.remove(del_path)
                    path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
                else:
                    if self.pswd is not None:
                        result = subprocess.run(["bash", "pextract", m_path, self.pswd])
                    else:
                        result = subprocess.run(["bash", "extract", m_path])
                    if result.returncode == 0:
                        os.remove(m_path)
                    else:
                        LOGGER.error("Failed to extract the archive")
                        path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
            except CompressExceptionHandler as err:
                LOGGER.info(err)
                path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
        else:
            path = f'{DOWNLOAD_DIR}{self.uid}/{name}'
        up_name = PurePath(path).name
        up_path = f'{DOWNLOAD_DIR}{self.uid}/{up_name}'
        size = get_path_size(up_path)
        LOGGER.info(f"Uploading: {up_name}")
        drive = GoogleDriveHelper(up_name, self)
        upload_status = UploadStatus(drive, size, gid, self)
        with download_dict_lock:
            download_dict[self.uid] = upload_status
        update_all_messages()
        drive.upload(up_name)

    def onDownloadError(self, error):
        error = error.replace('<', '').replace('>', '')
        clean_download(f'{DOWNLOAD_DIR}{self.uid}')
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        sendMessage(error, self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

    def onUploadComplete(self, link: str, size, files, folders, typ, name: str):
        msg = f'<b>Name:</b> <code>{escape(name)}</code>'
        msg += f'\n<b>Size:</b> {size}'
        msg += f'\n<b>Type: </b>{typ}'
        if os.path.isdir(f'{DOWNLOAD_DIR}{self.uid}/{name}'):
            msg += f'\n<b>SubFolders:</b> {folders}'
            msg += f'\n<b>Files:</b> {files}'
        msg += f'\n\n<b><a href="{link}">Drive Link</a></b>'
        if INDEX_URL is not None:
            url_path = requests.utils.quote(f'{name}')
            url = f'{INDEX_URL}/{url_path}'
            if os.path.isdir(f'{DOWNLOAD_DIR}/{self.uid}/{name}'):
                url += '/'
                msg += f'<b> | <a href="{url}">Index Link</a></b>'
            else:
                msg += f'<b> | <a href="{url}">Index Link</a></b>'
        sendMessage(msg, self.bot, self.message)
        clean_download(f'{DOWNLOAD_DIR}{self.uid}')
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

    def onUploadError(self, error):
        error = error.replace('<', '').replace('>', '')
        clean_download(f'{DOWNLOAD_DIR}{self.uid}')
        with download_dict_lock:
            try:
                del download_dict[self.uid]
            except Exception as e:
                LOGGER.error(str(e))
            count = len(download_dict)
        sendMessage(error, self.bot, self.message)
        if count == 0:
            self.clean()
        else:
            update_all_messages()

def _compress(bot, message, is_archive=False, is_extract=False, pswd=None):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(" ", maxsplit=1)
    reply_to = message.reply_to_message
    is_appdrive = False
    is_gdtot = False
    appdict = ''
    try:
        link = message_args[1]
        if link.startswith("pswd: "):
            raise IndexError
    except:
        link = ''
    link = re.split(r"pswd:| \|", link)[0]
    link = link.strip()
    pswdMsg = mesg[0].split(' pswd: ')
    if len(pswdMsg) > 1:
        pswd = pswdMsg[1]
    if reply_to is not None:
        reply_text = reply_to.text
        link = reply_text.strip()
    is_appdrive = is_appdrive_link(link)
    is_gdtot = is_gdtot_link(link)
    if any([is_appdrive, is_gdtot]):
        msg = sendMessage(f"<b>Processing:</b> <code>{link}</code>", bot, message)
        LOGGER.info(f"Processing: {link}")
        try:
            if is_appdrive:
                appdict = appdrive(link)
                link = appdict.get('gdrive_link')
            if is_gdtot:
                link = gdtot(link)
            deleteMessage(bot, msg)
        except DDLExceptionHandler as e:
            deleteMessage(bot, msg)
            LOGGER.error(e)
            return sendMessage(str(e), bot, message)
    listener = CompressListener(bot, message, is_archive, is_extract, pswd)
    if is_gdrive_link(link):
        threading.Thread(target=add_gd_download, args=(link, listener, is_appdrive, appdict, is_gdtot)).start()
    else:
        help_msg = '<b><u>Instructions</u></b>\nSend a link along with command'
        help_msg += '\n\n<b><u>Supported Sites</u></b>\n• Google Drive\n• AppDrive\n• GDToT'
        help_msg += '\n\n<b><u>Set Password</u></b>\nAdd "<code>pswd: xxx</code>" after the link'
        sendMessage(help_msg, bot, message)


def archive_data(update, context):
    _compress(context.bot, update.message, is_archive=True)

def extract_data(update, context):
    _compress(context.bot, update.message, is_extract=True)

archive_handler = CommandHandler(BotCommands.ArchiveCommand, archive_data,
                                 filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
extract_handler = CommandHandler(BotCommands.ExtractCommand, extract_data,
                                 filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(archive_handler)
dispatcher.add_handler(extract_handler)
