import logging
import os
import json
import re
import requests
import time

from io import FileIO
from urllib.parse import parse_qs, urlparse
from random import randrange
from telegraph.exceptions import RetryAfterError
from tenacity import retry, wait_exponential, stop_after_attempt, \
    retry_if_exception_type, RetryError

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from bot import LOGGER, DRIVE_NAMES, DRIVE_IDS, INDEX_URLS, DRIVE_FOLDER_ID, \
    IS_TEAM_DRIVE, TELEGRAPH, USE_SERVICE_ACCOUNTS, INDEX_URL
from bot.helper.ext_utils.bot_utils import SetInterval, get_readable_file_size
from bot.helper.ext_utils.fs_utils import get_mime_type
from bot.helper.telegram_helper.button_builder import ButtonMaker

logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

if USE_SERVICE_ACCOUNTS:
    SERVICE_ACCOUNTS_NUMBER = len(os.listdir("accounts"))

TELEGRAPH_LIMIT = 60

class GoogleDriveHelper:

    def __init__(self, name=None, path=None, size=0, listener=None):
        self.__OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__G_DRIVE_BASE_DOWNLOAD_URL = "https://drive.google.com/uc?id={}&export=download"
        self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self.__path = path
        self.__size = size
        self.__listener = listener
        self.__total_bytes = 0
        self.__total_folders = 0
        self.__total_files = 0
        self.__sa_count = 0
        self.__service_account_index = 0
        self.__start_time = 0
        self.__total_time = 0
        self.__alt_auth = False
        self.__is_uploading = False
        self.__is_downloading = False
        self.__is_cloning = False
        self.__is_cancelled = False
        self.__is_errored = False
        self.__status = None
        self.__updater = None
        self.__update_interval = 3
        self._file_processed_bytes = 0
        self.name = name
        self.processed_bytes = 0
        self.transferred_size = 0
        self.response = {}
        self.telegraph_path = []
        self.telegraph_content = []
        self.__service = self.__authorize()

    def speed(self):
        """
        It calculates the average Upload or Download speed and returns it in bytes/seconds unit
        :return: Upload or Download speed in bytes/second
        """
        try:
            return self.processed_bytes / self.__total_time
        except:
            return 0

    def cspeed(self):
        """
        It calculates the average clone speed and returns it in bytes/seconds unit
        :return: Clone speed in bytes/second
        """
        try:
            return self.transferred_size / int(time.time() - self.__start_time)
        except:
            return 0

    def __authorize(self):
        creds = None
        if USE_SERVICE_ACCOUNTS:
            if self.__sa_count == 0:
                self.__service_account_index = randrange(SERVICE_ACCOUNTS_NUMBER)
            LOGGER.info(f"Authorizing with {self.__service_account_index}.json file")
            creds = service_account.Credentials.from_service_account_file(
                f'accounts/{self.__service_account_index}.json', scopes=self.__OAUTH_SCOPE)
        elif os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.__OAUTH_SCOPE)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        else:
            LOGGER.error("The token.json file is missing")
        return build('drive', 'v3', credentials=creds, cache_discovery=False)

    def __alt_authorize(self):
        creds = None
        if USE_SERVICE_ACCOUNTS and not self.__alt_auth:
            self.__alt_auth = True
            if os.path.exists('token.json'):
                LOGGER.info("Authorizing with token.json file")
                creds = Credentials.from_authorized_user_file('token.json', self.__OAUTH_SCOPE)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                return build('drive', 'v3', credentials=creds, cache_discovery=False)
            else:
                LOGGER.error("The token.json file is missing")
        return None

    def __get_access_token(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.__OAUTH_SCOPE)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds.token

    def __switchServiceAccount(self):
        if self.__service_account_index == SERVICE_ACCOUNTS_NUMBER - 1:
            self.__service_account_index = 0
        else:
            self.__service_account_index += 1
        self.__sa_count += 1
        LOGGER.info(f"Switching SA to {self.__service_account_index}.json file")
        self.__service = self.__authorize()

    @staticmethod
    def __getIdFromUrl(link: str):
        if "folders" in link or "file" in link:
            regex = r'https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)'
            res = re.search(regex, link)
            if res is None:
                raise IndexError("Drive ID not found")
            return res.group(3)
        parsed = urlparse(link)
        return parse_qs(parsed.query)['id'][0]

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def __getFileMetadata(self, file_id):
        return self.__service.files().get(
                   fileId=file_id,
                   supportsAllDrives=True,
                   fields='name, id, mimeType, size').execute()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def __getFilesByFolderId(self, folder_id):
        page_token = None
        query = f"'{folder_id}' in parents and trashed = false"
        files = []
        while True:
            response = self.__service.files().list(
                           supportsAllDrives=True,
                           includeItemsFromAllDrives=True,
                           q=query,
                           spaces='drive',
                           pageSize=200,
                           fields='nextPageToken, files(id, name, mimeType, size, shortcutDetails)',
                           orderBy='folder, name',
                           pageToken=page_token).execute()
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return files

    def fileinfo(self, link):
        try:
            file_id = self.__getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg, "", "", "", "", ""
        try:
            access_token = self.__get_access_token()
            meta = self.__getFileMetadata(file_id)
            name = meta.get("name")
            size = get_readable_file_size(int(meta.get("size", 0)))
            mime_type = meta.get("mimeType")
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            if "File not found" in err:
                token_service = self.__alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.fileinfo(link)
                msg = "File not found"
            else:
                msg = err
            LOGGER.error(msg)
            return msg, "", "", "", "", ""
        return "", file_id, access_token, name, size, mime_type

    def __gDrive_file(self, filee):
        size = int(filee.get('size', 0))
        self.__total_bytes += size

    def __gDrive_directory(self, drive_folder):
        files = self.__getFilesByFolderId(drive_folder['id'])
        if len(files) == 0:
            return
        for filee in files:
            shortcut_details = filee.get('shortcutDetails')
            if shortcut_details is not None:
                mime_type = shortcut_details['targetMimeType']
                file_id = shortcut_details['targetId']
                filee = self.__getFileMetadata(file_id)
            else:
                mime_type = filee.get('mimeType')
            if mime_type == self.__G_DRIVE_DIR_MIME_TYPE:
                self.__total_folders += 1
                self.__gDrive_directory(filee)
            else:
                self.__total_files += 1
                self.__gDrive_file(filee)

    def helper(self, link):
        try:
            file_id = self.__getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg, "", "", ""
        try:
            meta = self.__getFileMetadata(file_id)
            name = meta.get('name')
            if meta.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                self.__gDrive_directory(meta)
            else:
                self.__total_files += 1
                self.__gDrive_file(meta)
            size = self.__total_bytes
            files = self.__total_files
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            if "File not found" in err:
                token_service = self.__alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.helper(link)
                msg = "File not found"
            else:
                msg = err
            LOGGER.error(msg)
            return msg, "", "", ""
        return "", size, name, files

    def deleteFile(self, link: str):
        try:
            file_id = self.__getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg
        msg = ''
        try:
            self.__service.files().delete(
                fileId=file_id,
                supportsAllDrives=True).execute()
            msg = "Permanently deleted"
        except HttpError as err:
            err = str(err).replace('>', '').replace('<', '')
            if "File not found" in err:
                msg = "File not found"
            elif "insufficientFilePermissions" in err:
                token_service = self.__alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.deleteFile(link)
                msg = "Insufficient file permissions"
            else:
                msg = err
            LOGGER.error(msg)
        return msg

    def __set_permission_public(self, file_id):
        permissions = {
            'type': 'anyone',
            'role': 'reader'
        }
        return self.__service.permissions().create(
                   fileId=file_id,
                   body=permissions,
                   supportsAllDrives=True).execute()

    def __set_permission_email(self, file_id, email):
        permissions = {
            'type': 'user',
            'role': 'reader',
            'emailAddress': email
        }
        return self.__service.permissions().create(
                   fileId=file_id,
                   body=permissions,
                   supportsAllDrives=True,
                   sendNotificationEmail=False).execute()

    def setPermission(self, link, access):
        try:
            file_id = self.__getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg
        msg = ''
        try:
            if access != '':
                self.__set_permission_email(file_id, access)
                msg = f"Added <code>{access}</code> as viewer"
            else:
                self.__set_permission_public(file_id)
                msg = "Set permission to <code>Anyone with the link</code>"
        except HttpError as err:
            err = str(err).replace('>', '').replace('<', '')
            if "File not found" in err:
                msg = "File not found"
            elif "insufficientFilePermissions" in err:
                token_service = self.__alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.setPermission(link, access)
                msg = "Insufficient file permissions"
            else:
                msg = err
            LOGGER.error(msg)
        return msg

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def __create_directory(self, directory_name, dest_id):
        file_metadata = {
            "name": directory_name,
            "mimeType": self.__G_DRIVE_DIR_MIME_TYPE
        }
        if dest_id is not None:
            file_metadata["parents"] = [dest_id]
        file = self.__service.files().create(
                   body=file_metadata,
                   supportsAllDrives=True).execute()
        file_id = file.get("id")
        if not IS_TEAM_DRIVE:
            self.__set_permission_public(file_id)
        return file_id

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def __copyFile(self, file_id, dest_id):
        body = {
            'parents': [dest_id]
        }
        try:
            res = self.__service.files().copy(
                      fileId=file_id,
                      body=body,
                      supportsAllDrives=True).execute()
            return res
        except HttpError as err:
            if err.resp.get('content-type', '').startswith('application/json'):
                reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                if reason not in ['userRateLimitExceeded', 'dailyLimitExceeded']:
                    raise err
                if USE_SERVICE_ACCOUNTS:
                    if self.__sa_count >= SERVICE_ACCOUNTS_NUMBER:
                        LOGGER.info("SA switch limit exceeded")
                        raise err
                    else:
                        if self.__is_cancelled:
                            return
                        self.__switchServiceAccount()
                        return self.__copyFile(file_id, dest_id)
                else:
                    LOGGER.error(f"Warning: {reason}")
                    raise err

    def __cloneFolder(self, name, local_path, folder_id, dest_id):
        files = self.__getFilesByFolderId(folder_id)
        if len(files) == 0:
            return dest_id
        for file in files:
            if file.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                self.__total_folders += 1
                file_path = os.path.join(local_path, file.get('name'))
                current_dir_id = self.__create_directory(file.get('name'), dest_id)
                self.__cloneFolder(file.get('name'), file_path, file.get('id'), current_dir_id)
            else:
                self.__total_files += 1
                self.transferred_size += int(file.get('size', 0))
                self.__copyFile(file.get('id'), dest_id)
            if self.__is_cancelled:
                break

    def clone(self, link, __dest_id):
        self.__is_cloning = True
        self.__start_time = time.time()
        self.__total_files = 0
        self.__total_folders = 0
        try:
            file_id = self.__getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg
        if __dest_id != "":
            dest_id = __dest_id
            index_url = None
        else:
            dest_id = DRIVE_FOLDER_ID
            index_url = INDEX_URL
        msg = ""
        try:
            meta = self.__getFileMetadata(file_id)
            name = meta.get("name")
            mime_type = meta.get("mimeType")
            if mime_type == self.__G_DRIVE_DIR_MIME_TYPE:
                dir_id = self.__create_directory(meta.get('name'), dest_id)
                self.__cloneFolder(meta.get('name'), meta.get('name'), meta.get('id'), dir_id)
                durl = self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)
                if self.__is_cancelled:
                    LOGGER.info(f"Deleting cloned data from Drive")
                    self.deleteFile(durl)
                    return "The clone task has been cancelled"
                msg += f'<b>Name:</b> <code>{name}</code>'
                msg += f'\n<b>Size:</b> {get_readable_file_size(self.transferred_size)}'
                msg += f'\n<b>Type:</b> Folder'
                msg += f'\n<b>SubFolders:</b> {self.__total_folders}'
                msg += f'\n<b>Files:</b> {self.__total_files}'
                msg += f'\n\n<b><a href="{self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)}">Drive Link</a></b>'
                if index_url is not None:
                    url_path = requests.utils.quote(f'{meta.get("name")}', safe='')
                    url = f'{index_url}/{url_path}/'
                    msg += f'<b> | <a href="{url}">Index Link</a></b>'
            else:
                file = self.__copyFile(meta.get('id'), dest_id)
                msg += f'<b>Name:</b> <code>{file.get("name")}</code>'
                if mime_type is None:
                    mime_type = 'File'
                msg += f'\n<b>Size:</b> {get_readable_file_size(int(meta.get("size", 0)))}'
                msg += f'\n<b>Type:</b> {mime_type}'
                msg += f'\n\n<b><a href="{self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get("id"))}">Drive Link</a></b>'
                if index_url is not None:
                    url_path = requests.utils.quote(f'{file.get("name")}', safe='')
                    url = f'{index_url}/{url_path}'
                    msg += f'<b> | <a href="{url}">Index Link</a></b>'
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            if "User rate limit exceeded" in err:
                msg = "User rate limit exceeded"
            elif "File not found" in err:
                token_service = self.__alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.clone(link, __dest_id)
                msg = "File not found"
            else:
                msg = err
            LOGGER.error(msg)
        return msg

    def count(self, link):
        try:
            file_id = self.__getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg
        msg = ""
        try:
            meta = self.__getFileMetadata(file_id)
            mime_type = meta.get('mimeType')
            if mime_type == self.__G_DRIVE_DIR_MIME_TYPE:
                self.__gDrive_directory(meta)
                msg += f'<b>Name:</b> <code>{meta.get("name")}</code>'
                msg += f'\n<b>Size:</b> {get_readable_file_size(self.__total_bytes)}'
                msg += f'\n<b>Type:</b> Folder'
                msg += f'\n<b>SubFolders:</b> {self.__total_folders}'
            else:
                msg += f'<b>Name: </b><code>{meta.get("name")}</code>'
                if mime_type is None:
                    mime_type = 'File'
                self.__total_files += 1
                self.__gDrive_file(meta)
                msg += f'\n<b>Size:</b> {get_readable_file_size(self.__total_bytes)}'
                msg += f'\n<b>Type:</b> {mime_type}'
            msg += f'\n<b>Files:</b> {self.__total_files}'
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            if "File not found" in err:
                token_service = self.__alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.count(link)
                msg = "File not found"
            else:
                msg = err
            LOGGER.error(msg)
        return msg

    def _progress(self):
        if self.__status is not None:
            chunk_size = self.__status.total_size * self.__status.progress() - self._file_processed_bytes
            self._file_processed_bytes = self.__status.total_size * self.__status.progress()
            self.processed_bytes += chunk_size
            self.__total_time += self.__update_interval

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=(retry_if_exception_type(Exception)))
    def __upload_file(self, file_path, file_name, mime_type, dest_id):
        file_metadata = {
            'name': file_name,
            'mimeType': mime_type
        }
        if dest_id is not None:
            file_metadata['parents'] = [dest_id]
        if os.path.getsize(file_path) == 0:
            media_body = MediaFileUpload(file_path, mimetype=mime_type, resumable=False)
            response = self.__service.files().create(
                           body=file_metadata,
                           media_body=media_body,
                           supportsAllDrives=True).execute()
            if not IS_TEAM_DRIVE:
                self.__set_permission_public(response['id'])
            drive_file = self.__service.files().get(
                             fileId=response['id'],
                             supportsAllDrives=True).execute()
            download_url = self.__G_DRIVE_BASE_DOWNLOAD_URL.format(drive_file.get('id'))
            return download_url
        media_body = MediaFileUpload(file_path, mimetype=mime_type, resumable=True,
                                     chunksize=50 * 1024 * 1024)
        drive_file = self.__service.files().create(
                         body=file_metadata,
                         media_body=media_body,
                         supportsAllDrives=True)
        response = None
        while response is None and not self.__is_cancelled:
            try:
                self.__status, response = drive_file.next_chunk()
            except HttpError as err:
                if err.resp.get('content-type', '').startswith('application/json'):
                    reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                    if reason not in ['userRateLimitExceeded', 'dailyLimitExceeded']:
                        raise err
                    if USE_SERVICE_ACCOUNTS:
                        if self.__sa_count >= SERVICE_ACCOUNTS_NUMBER:
                            LOGGER.info("SA switch limit exceeded")
                            raise err
                        else:
                            if self.__is_cancelled:
                                return
                            self.__switchServiceAccount()
                            LOGGER.info(f"Warning: {reason}")
                            return self.__upload_file(file_path, file_name, mime_type, dest_id)
                    else:
                        LOGGER.error(f"Warning: {reason}")
                        raise err
        if self.__is_cancelled:
            return
        self._file_processed_bytes = 0
        if not IS_TEAM_DRIVE:
            self.__set_permission_public(response['id'])
        drive_file = self.__service.files().get(
                         fileId=response['id'],
                         supportsAllDrives=True).execute()
        download_url = self.__G_DRIVE_BASE_DOWNLOAD_URL.format(drive_file.get('id'))
        return download_url

    def __upload_dir(self, input_directory, dest_id):
        list_dirs = os.listdir(input_directory)
        if len(list_dirs) == 0:
            return dest_id
        new_id = None
        for item in list_dirs:
            current_file_name = os.path.join(input_directory, item)
            if os.path.isdir(current_file_name):
                current_dir_id = self.__create_directory(item, dest_id)
                new_id = self.__upload_dir(current_file_name, current_dir_id)
                self.__total_folders += 1
            else:
                mime_type = get_mime_type(current_file_name)
                file_name = current_file_name.split("/")[-1]
                # 'current_file_name' will have the full path
                self.__upload_file(current_file_name, file_name, mime_type, dest_id)
                self.__total_files += 1
                new_id = dest_id
            if self.__is_cancelled:
                break
        return new_id

    def upload(self, file_name: str):
        self.__is_uploading = True
        file_path = f"{self.__path}/{file_name}"
        size = get_readable_file_size(self.__size)
        self.__updater = SetInterval(self.__update_interval, self._progress)
        try:
            if os.path.isfile(file_path):
                mime_type = get_mime_type(file_path)
                link = self.__upload_file(file_path, file_name, mime_type, DRIVE_FOLDER_ID)
                if self.__is_cancelled:
                    return
                if link is None:
                    raise Exception("The upload task has been manually cancelled")
            else:
                mime_type = 'Folder'
                dir_id = self.__create_directory(os.path.basename(os.path.abspath(file_name)), DRIVE_FOLDER_ID)
                result = self.__upload_dir(file_path, dir_id)
                if result is None:
                    raise Exception("The upload task has been manually cancelled")
                link = f"https://drive.google.com/folderview?id={dir_id}"
                if self.__is_cancelled:
                    return
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            self.__listener.onUploadError(str(err))
            self.__is_errored = True
        finally:
            self.__updater.cancel()
            if self.__is_cancelled and not self.__is_errored:
                if mime_type == 'Folder':
                    LOGGER.info("Deleting uploaded data from Drive")
                    link = f"https://drive.google.com/folderview?id={dir_id}"
                    self.deleteFile(link)
                return
            elif self.__is_errored:
                return
        self.__listener.onUploadComplete(link, size, self.__total_files, self.__total_folders, mime_type, self.name)

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=(retry_if_exception_type(Exception)))
    def __download_file(self, file_id, path, filename, mime_type):
        request = self.__service.files().get_media(
                      fileId=file_id,
                      supportsAllDrives=True)
        filename = filename.replace('/', '')
        if len(filename.encode()) > 255:
            ext = os.path.splitext(filename)[1]
            filename = f"{filename[:245]}{ext}"
            if self.name.endswith(ext):
                self.name = filename
        if self.__is_cancelled:
            return
        fh = FileIO(f"{path}/{filename}", 'wb')
        downloader = MediaIoBaseDownload(fh, request, chunksize=50 * 1024 * 1024)
        done = False
        while not done:
            if self.__is_cancelled:
                fh.close()
                break
            try:
                self.__status, done = downloader.next_chunk()
            except HttpError as err:
                if err.resp.get('content-type', '').startswith('application/json'):
                    reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                    if reason not in ['downloadQuotaExceeded', 'dailyLimitExceeded']:
                        raise err
                    if USE_SERVICE_ACCOUNTS:
                        if self.__sa_count >= SERVICE_ACCOUNTS_NUMBER:
                            LOGGER.info("SA switch limit exceeded")
                            raise err
                        else:
                            if self.__is_cancelled:
                                return
                            self.__switchServiceAccount()
                            LOGGER.info(f"Warning: {reason}")
                            return self.__download_file(file_id, path, filename, mime_type)
                    else:
                        LOGGER.error(f"Warning: {reason}")
                        raise err
        self._file_processed_bytes = 0

    def __download_folder(self, folder_id, path, folder_name):
        folder_name = folder_name.replace('/', '')
        if not os.path.exists(f"{path}/{folder_name}"):
            os.makedirs(f"{path}/{folder_name}")
        path += f"/{folder_name}"
        result = self.__getFilesByFolderId(folder_id)
        if len(result) == 0:
            return
        result = sorted(result, key=lambda k: k['name'])
        for item in result:
            file_id = item['id']
            filename = item['name']
            shortcut_details = item.get('shortcutDetails')
            if shortcut_details is not None:
                file_id = shortcut_details['targetId']
                mime_type = shortcut_details['targetMimeType']
            else:
                mime_type = item.get('mimeType')
            if mime_type == self.__G_DRIVE_DIR_MIME_TYPE:
                self.__download_folder(file_id, path, filename)
            elif not os.path.isfile(f"{path}{filename}"):
                self.__download_file(file_id, path, filename, mime_type)
            if self.__is_cancelled:
                break

    def download(self, link):
        self.__is_downloading = True
        file_id = self.__getIdFromUrl(link)
        self.__updater = SetInterval(self.__update_interval, self._progress)
        try:
            meta = self.__getFileMetadata(file_id)
            if meta.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
                self.__download_folder(file_id, self.__path, self.name)
            else:
                os.makedirs(self.__path, exist_ok=True)
                self.__download_file(file_id, self.__path, self.name, meta.get('mimeType'))
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            if "downloadQuotaExceeded" in err:
                err = "Download quota exceeded"
            elif "File not found" in err:
                token_service = self.__alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    self.__updater.cancel()
                    return self.download(link)
            self.__listener.onDownloadError(err)
            self.__is_cancelled = True
        finally:
            self.__updater.cancel()
            if self.__is_cancelled:
                return
        self.__listener.onDownloadComplete()

    def cancel_task(self):
        self.__is_cancelled = True
        if self.__is_downloading:
            LOGGER.info(f"Cancelling download: {self.name}")
            self.__listener.onDownloadError("The download task has been cancelled")
        elif self.__is_cloning:
            LOGGER.info(f"Cancelling clone: {self.name}")
        elif self.__is_uploading:
            LOGGER.info(f"Cancelling upload: {self.name}")
            self.__listener.onUploadError("The upload task has been cancelled")

    def __escapes(self, str_val):
        chars = ['\\', "'", '"', r'\a', r'\b', r'\f', r'\n', r'\r', r'\t']
        for char in chars:
            str_val = str_val.replace(char, f'\\{char}')
        return str_val

    def __create_page(self, acc, content):
        try:
            self.telegraph_path.append(
                acc.create_page(
                    title="SearchX",
                    author_name="Levi",
                    author_url="https://t.me/l3v11",
                    html_content=content)['path'])
        except RetryAfterError as err:
            LOGGER.info(f"Cooldown: {err.retry_after} seconds")
            time.sleep(err.retry_after)
            self.__create_page(acc, content)

    def __edit_page(self, acc, content, path):
        try:
            acc.edit_page(
                path=path,
                title="SearchX",
                author_name="Levi",
                author_url="https://t.me/l3v11",
                html_content=content)
        except RetryAfterError as err:
            LOGGER.info(f"Cooldown: {err.retry_after} seconds")
            time.sleep(err.retry_after)
            self.__edit_page(acc, content, path)

    def __receive_callback(self, request_id, response, exception):
        if exception is not None:
            exception = str(exception).replace('>', '').replace('<', '')
            LOGGER.error(exception)
        else: 
            if response['files']:
                self.response[request_id] = response

    def __drive_query(self, drive_ids, search_type, file_name):
        batch = self.__service.new_batch_http_request(self.__receive_callback)
        query = f"name contains '{file_name}' and "
        if search_type is not None:
            if search_type == '-d':
                query += "mimeType = 'application/vnd.google-apps.folder' and "
            elif search_type == '-f':
                query += "mimeType != 'application/vnd.google-apps.folder' and "
        query += "trashed=false"
        for drive_id in drive_ids:
            if drive_id == "root":
                batch.add(
                    self.__service.files().list(
                        q=f"{query} and 'me' in owners",
                        pageSize=1000,
                        spaces='drive',
                        fields='files(id, name, mimeType, size)',
                        orderBy='folder, name'))
            else:
                batch.add(
                    self.__service.files().list(
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        driveId=drive_id,
                        q=query,
                        corpora='drive',
                        spaces='drive',
                        pageSize=1000,
                        fields='files(id, name, mimeType, size)',
                        orderBy='folder, name'))
        batch.execute()

    def drive_list(self, file_name):
        file_name = self.__escapes(file_name)
        search_type = None
        if re.search("^-d ", file_name, re.IGNORECASE):
            search_type = '-d'
            file_name = file_name[3: len(file_name)]
        elif re.search("^-f ", file_name, re.IGNORECASE):
            search_type = '-f'
            file_name = file_name[3: len(file_name)]
        msg = ''
        acc_no = -1
        page_per_acc = 2
        response_count = 0
        total_acc = len(TELEGRAPH)
        start_time = time.time()
        token_service = self.__alt_authorize()
        if token_service is not None:
            self.__service = token_service
        self.__drive_query(DRIVE_IDS, search_type, file_name)
        add_title_msg = True
        for files in self.response:
            index = int(files) - 1
            if add_title_msg:
                msg = f'<h4>Query: {file_name}</h4><br>'
                add_title_msg = False
            msg += f"╾────────────╼<br><b>{DRIVE_NAMES[index]}</b><br>╾────────────╼<br>"
            # Detect whether the current entity is a folder or a file
            for file in self.response[files]["files"]:
                if file.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                    msg += f"🗂️<code>{file.get('name')}</code> <b>(folder)</b><br>" \
                           f"<b><a href='https://drive.google.com/drive/folders/{file.get('id')}'>Drive Link</a></b>"
                    if INDEX_URLS[index] is not None:
                        url_path = requests.utils.quote(f"{file.get('name')}")
                        url = f"{INDEX_URLS[index]}search?q={url_path}"
                        msg += f"<b> | <a href='{url}'>Index Link</a></b>"
                else:
                    msg += f"📄<code>{file.get('name')}</code> <b>({get_readable_file_size(int(file.get('size', 0)))})" \
                           f"</b><br><b><a href='https://drive.google.com/uc?id={file.get('id')}" \
                           f"&export=download'>Drive Link</a></b>"
                    if INDEX_URLS[index] is not None:
                        url_path = requests.utils.quote(f"{file.get('name')}")
                        url = f"{INDEX_URLS[index]}search?q={url_path}"
                        msg += f"<b> | <a href='{url}'>Index Link</a></b>"
                msg += '<br><br>'
                response_count += 1
                if response_count % TELEGRAPH_LIMIT == 0:
                    self.telegraph_content.append(msg)
                    msg = ''

        if msg != '':
            self.telegraph_content.append(msg)
        total_pages = len(self.telegraph_content)
        if total_pages == 0:
            return "<b>Found nothing :(</b>", None

        for i in range(total_pages):
            if i % page_per_acc == 0:
                acc_no = (acc_no+1) % total_acc

            if i != 0:
                # Add previous page link
                self.telegraph_content[i] += f'<b><a href="https://graph.org/{self.telegraph_path[i-1]}">Previous</a>' \
                                             f' | Page {i+1}/{total_pages}</b>'
            else:
                self.telegraph_content[i] += f'<b>Page {i+1}/{total_pages}</b>'

            self.__create_page(
                TELEGRAPH[acc_no],
                self.telegraph_content[i])

            if i != 0:
                # Edit previous page to add next page link
                self.telegraph_content[i-1] += f'<b> | <a href="https://graph.org/{self.telegraph_path[i]}">Next</a></b>'

                self.__edit_page(
                    TELEGRAPH[(acc_no-1) if i % page_per_acc == 0 else acc_no],
                    self.telegraph_content[i-1],
                    self.telegraph_path[i-1])

        msg = f"<b>Found {response_count} results matching '{file_name}' in {len(DRIVE_IDS)} Drives</b> " \
              f"<b>(Time taken {round(time.time() - start_time, 2)}s)</b>"
        button = ButtonMaker()
        button.build_button("VIEW RESULTS 🗂️", f"https://graph.org/{self.telegraph_path[0]}")
        return msg, button.build_menu(1)
