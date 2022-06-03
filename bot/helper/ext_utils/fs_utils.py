import magic
import os
import shutil
import sys

from bot import LOGGER, DOWNLOAD_DIR
from bot.helper.ext_utils.exceptions import CompressExceptionHandler

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
    if orig_path.endswith(".tar.bz2"):
        return orig_path.rsplit(".tar.bz2", 1)[0]
    elif orig_path.endswith(".tar.gz"):
        return orig_path.rsplit(".tar.gz", 1)[0]
    elif orig_path.endswith(".bz2"):
        return orig_path.rsplit(".bz2", 1)[0]
    elif orig_path.endswith(".gz"):
        return orig_path.rsplit(".gz", 1)[0]
    elif orig_path.endswith(".tar.xz"):
        return orig_path.rsplit(".tar.xz", 1)[0]
    elif orig_path.endswith(".tar"):
        return orig_path.rsplit(".tar", 1)[0]
    elif orig_path.endswith(".tbz2"):
        return orig_path.rsplit("tbz2", 1)[0]
    elif orig_path.endswith(".tgz"):
        return orig_path.rsplit(".tgz", 1)[0]
    elif orig_path.endswith(".zip"):
        return orig_path.rsplit(".zip", 1)[0]
    elif orig_path.endswith(".7z"):
        return orig_path.rsplit(".7z", 1)[0]
    elif orig_path.endswith(".Z"):
        return orig_path.rsplit(".Z", 1)[0]
    elif orig_path.endswith(".rar"):
        return orig_path.rsplit(".rar", 1)[0]
    elif orig_path.endswith(".iso"):
        return orig_path.rsplit(".iso", 1)[0]
    elif orig_path.endswith(".wim"):
        return orig_path.rsplit(".wim", 1)[0]
    elif orig_path.endswith(".cab"):
        return orig_path.rsplit(".cab", 1)[0]
    elif orig_path.endswith(".apm"):
        return orig_path.rsplit(".apm", 1)[0]
    elif orig_path.endswith(".arj"):
        return orig_path.rsplit(".arj", 1)[0]
    elif orig_path.endswith(".chm"):
        return orig_path.rsplit(".chm", 1)[0]
    elif orig_path.endswith(".cpio"):
        return orig_path.rsplit(".cpio", 1)[0]
    elif orig_path.endswith(".cramfs"):
        return orig_path.rsplit(".cramfs", 1)[0]
    elif orig_path.endswith(".deb"):
        return orig_path.rsplit(".deb", 1)[0]
    elif orig_path.endswith(".dmg"):
        return orig_path.rsplit(".dmg", 1)[0]
    elif orig_path.endswith(".fat"):
        return orig_path.rsplit(".fat", 1)[0]
    elif orig_path.endswith(".hfs"):
        return orig_path.rsplit(".hfs", 1)[0]
    elif orig_path.endswith(".lzh"):
        return orig_path.rsplit(".lzh", 1)[0]
    elif orig_path.endswith(".lzma"):
        return orig_path.rsplit(".lzma", 1)[0]
    elif orig_path.endswith(".lzma2"):
        return orig_path.rsplit(".lzma2", 1)[0]
    elif orig_path.endswith(".mbr"):
        return orig_path.rsplit(".mbr", 1)[0]
    elif orig_path.endswith(".msi"):
        return orig_path.rsplit(".msi", 1)[0]
    elif orig_path.endswith(".mslz"):
        return orig_path.rsplit(".mslz", 1)[0]
    elif orig_path.endswith(".nsis"):
        return orig_path.rsplit(".nsis", 1)[0]
    elif orig_path.endswith(".ntfs"):
        return orig_path.rsplit(".ntfs", 1)[0]
    elif orig_path.endswith(".rpm"):
        return orig_path.rsplit(".rpm", 1)[0]
    elif orig_path.endswith(".squashfs"):
        return orig_path.rsplit(".squashfs", 1)[0]
    elif orig_path.endswith(".udf"):
        return orig_path.rsplit(".udf", 1)[0]
    elif orig_path.endswith(".vhd"):
        return orig_path.rsplit(".vhd", 1)[0]
    elif orig_path.endswith(".xar"):
        return orig_path.rsplit(".xar", 1)[0]
    else:
        raise CompressExceptionHandler('Unsupported file format')

def get_mime_type(file_path):
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    mime_type = mime_type or "text/plain"
    return mime_type
