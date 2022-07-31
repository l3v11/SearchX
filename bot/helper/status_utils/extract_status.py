import time

from bot import LOGGER, DOWNLOAD_DIR
from bot.helper.ext_utils.bot_utils import TaskStatus, get_readable_file_size, get_readable_time
from bot.helper.ext_utils.fs_utils import get_path_size

class ExtractStatus:
    def __init__(self, name, size, gid, listener):
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.__uid = listener.uid
        self.__start_time = time.time()
        self.message = listener.message

    def gid(self) -> str:
        return self.__gid

    def progress_raw(self):
        try:
            return self.processed_bytes() / self.__size * 100
        except:
            return 0

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed_raw(self):
        return self.processed_bytes() / (time.time() - self.__start_time)

    def speed(self):
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def name(self):
        return self.__name

    def size_raw(self):
        return self.__size

    def size(self):
        return get_readable_file_size(self.__size)

    def eta(self):
        try:
            seconds = (self.size_raw() - self.processed_bytes()) / self.speed_raw()
            return f'{get_readable_time(seconds)}'
        except:
            return '-'

    def status(self):
        return TaskStatus.STATUS_EXTRACTING

    def processed_bytes(self):
        return get_path_size(f"{DOWNLOAD_DIR}{self.__uid}") - self.__size

    def download(self):
        return self

    def cancel_task(self):
        LOGGER.info(f"Cancelling extract: {self.__name}")
        if self.__listener.suproc is not None:
            self.__listener.suproc.kill()
        self.__listener.onUploadError("The extract task has been cancelled")
