import random
import string

from bot import LOGGER, ARCHIVE_LIMIT, download_dict, download_dict_lock
from bot.helper.drive_utils.gdriveTools import GoogleDriveHelper
from bot.helper.status_utils.download_status import DownloadStatus
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, sendStatusMessage
from bot.helper.ext_utils.bot_utils import get_readable_file_size

def add_gd_download(link, path, listener, customname, is_gdtot):
    msg = sendMessage(f"<b>Checking:</b> <code>{link}</code>", listener.bot, listener.message)
    LOGGER.info(f"Checking: {link}")
    gd = GoogleDriveHelper()
    res, size, name, files = gd.helper(link)
    deleteMessage(listener.bot, msg)
    if res != "":
        return sendMessage(res, listener.bot, listener.message)
    if customname:
        name = customname
    if ARCHIVE_LIMIT is not None:
        if size > ARCHIVE_LIMIT * 1024**3:
            msg2 = f"<b>Name:</b> <code>{name}</code>"
            msg2 += f"\n<b>Size:</b> {get_readable_file_size(size)}"
            msg2 += f"\n<b>Limit:</b> {ARCHIVE_LIMIT} GB"
            msg2 += "\n\n<b>⚠️ Task failed</b>"
            return sendMessage(msg2, listener.bot, listener.message)
    LOGGER.info(f"Downloading: {name}")
    drive = GoogleDriveHelper(name, path, size, listener)
    gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
    download_status = DownloadStatus(drive, size, listener, gid)
    with download_dict_lock:
        download_dict[listener.uid] = download_status
    sendStatusMessage(listener.message, listener.bot)
    drive.download(link)
    if is_gdtot:
        LOGGER.info(f"Deleting: {link}")
        drive.deleteFile(link)
