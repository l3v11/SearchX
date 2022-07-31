import magic
import os
import re
import shutil
import sys

from bot import LOGGER, DOWNLOAD_DIR
from bot.helper.ext_utils.exceptions import CompressExceptionHandler

ARCH_EXT = [".tar.bz2", ".tar.gz", ".bz2", ".gz", ".tar.xz", ".tar", ".tbz2", ".tgz", ".lzma2",
                ".zip", ".7z", ".z", ".rar", ".iso", ".wim", ".cab", ".apm", ".arj", ".chm",
                ".cpio", ".cramfs", ".deb", ".dmg", ".fat", ".hfs", ".lzh", ".lzma", ".mbr",
                ".msi", ".mslz", ".nsis", ".ntfs", ".rpm", ".squashfs", ".udf", ".vhd", ".xar"]

def clean_download(path: str):
    if os.path.exists(path):
        LOGGER.info(f"Cleaning: {path}")
        try:
            shutil.rmtree(path)
        except:
            pass

def start_cleanup():
    try:
        shutil.rmtree(DOWNLOAD_DIR)
    except:
        pass
    os.makedirs(DOWNLOAD_DIR)

def clean_all():
    try:
        shutil.rmtree(DOWNLOAD_DIR)
    except:
        pass

def exit_clean_up(signal, frame):
    try:
        LOGGER.info("Cleaning up the downloads and exiting")
        clean_all()
        sys.exit(0)
    except KeyboardInterrupt:
        LOGGER.warning("Force exiting before the cleanup finishes")
        sys.exit(1)

def get_path_size(path: str):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total_size = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            abs_path = os.path.join(root, f)
            total_size += os.path.getsize(abs_path)
    return total_size

def get_base_name(orig_path: str):
    ext = [ext for ext in ARCH_EXT if orig_path.lower().endswith(ext)]
    if len(ext) > 0:
        ext = ext[0]
        return re.split(ext + '$', orig_path, maxsplit=1, flags=re.I)[0]
    else:
        raise CompressExceptionHandler('Unsupported file format')

def get_mime_type(file_path):
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    mime_type = mime_type or "text/plain"
    return mime_type
