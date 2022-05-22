import re
import threading
import time

from html import escape
from psutil import virtual_memory, cpu_percent

from bot.helper.telegram_helper.bot_commands import BotCommands
from bot import botStartTime, download_dict, download_dict_lock

SIZE_UNITS = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']

class SetInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = threading.Event()
        thread = threading.Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time.time() + self.interval
        while not self.stopEvent.wait(nextTime - time.time()):
            nextTime += self.interval
            self.action()

    def cancel(self):
        self.stopEvent.set()

def getDownloadByGid(gid):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            if dl.gid() == gid:
                return dl
    return None

def get_progress_bar_string(status):
    completed = status.processed_bytes() / 8
    total = status.size_raw() / 8
    p = 0 if total == 0 else round(completed * 100 / total)
    p = min(max(p, 0), 100)
    cFull = p // 8
    p_str = '⬤' * cFull
    p_str += '○' * (12 - cFull)
    p_str = f"[{p_str}]"
    return p_str

def get_readable_message():
    with download_dict_lock:
        msg = ""
        for download in list(download_dict.values()):
            msg += f"<b>Name:</b> <code>{escape(str(download.name()))}</code>"
            msg += f"\n{get_progress_bar_string(download)} {download.progress()}"
            msg += f"\n<b>Size:</b> {get_readable_file_size(download.processed_bytes())} / {download.size()}"
            msg += f"\n<b>Transfers:</b> {download.processed_files()} / {download.files()}"
            msg += f"\n<b>Speed:</b> {download.speed()}"
            msg += f"\n<b>ETA:</b> {download.eta()}"
            msg += f"\n<code>/{BotCommands.CancelCommand} {download.gid()}</code>"
            msg += "\n\n"
        sysmsg = "━━━━━━━━━━━━━━━"
        sysmsg += f"\n<b>CPU:</b> {cpu_percent()}% | <b>RAM:</b> {virtual_memory().percent}%"
        sysmsg += f"\n<b>UPTIME:</b> {get_readable_time(time.time() - botStartTime)}"
        return msg + sysmsg

def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None:
        return '0 B'
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f'{round(size_in_bytes, 2)} {SIZE_UNITS[index]}'
    except IndexError:
        return 'File too large'

def get_readable_time(seconds: int) -> str:
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days}d'
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours}h'
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes}m'
    seconds = int(seconds)
    result += f'{seconds}s'
    return result

def is_gdrive_link(url: str):
    return "drive.google.com" in url

def is_appdrive_link(url: str):
    url = re.match(r'https?://(appdrive|driveapp)\.in/\S+', url)
    return bool(url)

def is_gdtot_link(url: str):
    url = re.match(r'https?://.+\.gdtot\.\S+', url)
    return bool(url)

def new_thread(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper
