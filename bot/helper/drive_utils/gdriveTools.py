import logging
import os
import json
import re
import requests
import time

from io import FileIO
from urllib.parse import parse_qs, urlparse
from random import randrange
from tenacity import retry, wait_exponential, stop_after_attempt, \
    retry_if_exception_type, before_log, RetryError

from telegram import InlineKeyboardMarkup
from telegraph.exceptions import RetryAfterError

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from bot import LOGGER, DOWNLOAD_DIR, DRIVE_NAMES, DRIVE_IDS, INDEX_URLS, PARENT_ID, \
    IS_TEAM_DRIVE, TELEGRAPH, USE_SERVICE_ACCOUNTS, INDEX_URL, DEST_DRIVES
from bot.helper.ext_utils.bot_utils import SetInterval, get_readable_file_size
from bot.helper.ext_utils.fs_utils import get_mime_type, get_path_size
from bot.helper.telegram_helper.button_builder import ButtonMaker

logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

if USE_SERVICE_ACCOUNTS:
    SERVICE_ACCOUNT_INDEX = randrange(len(os.listdir("accounts")))

TELEGRAPH_LIMIT = 60

class GoogleDriveHelper:
    def __init__(self, name=None, listener=None):
        # Check https://developers.google.com/drive/scopes for all available scopes
        self.__OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__G_DRIVE_BASE_DOWNLOAD_URL = "https://drive.google.com/uc?id={}&export=download"
        self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self.__listener = listener
        self.__service = self.authorize()
        self._file_uploaded_bytes = 0
        self._file_downloaded_bytes = 0
        self.uploaded_bytes = 0
        self.downloaded_bytes = 0
        self.start_time = 0
        self.total_time = 0
        self.dtotal_time = 0
        self.is_uploading = False
        self.is_downloading = False
        self.is_cloning = False
        self.is_cancelled = False
        self.is_errored = False
        self.status = None
        self.dstatus = None
        self.updater = None
        self.name = name
        self.update_interval = 3
        self.total_bytes = 0
        self.total_files = 0
        self.total_folders = 0
        self.transferred_size = 0
        self.sa_count = 0
        self.alt_auth = False
        self.response = {}
        self.path = []
        self.telegraph_content = []
        self.title = "SearchX"
        self.author_name = "Levi"
        self.author_url = "https://t.me/l3v11"

    def speed(self):
        """
        It calculates the average upload speed and returns it in bytes/seconds unit
        :return: Upload speed in bytes/second
        """
        try:
            return self.uploaded_bytes / self.total_time
        except ZeroDivisionError:
            return 0

    def dspeed(self):
        """
        It calculates the average download speed and returns it in bytes/seconds unit
        :return: Download speed in bytes/second
        """
        try:
            return self.downloaded_bytes / self.dtotal_time
        except ZeroDivisionError:
            return 0

    def cspeed(self):
        """
        It calculates the average clone speed and returns it in bytes/seconds unit
        :return: Clone speed in bytes/second
        """
        try:
            return self.transferred_size / int(time.time() - self.start_time)
        except ZeroDivisionError:
            return 0

    def authorize(self):
        creds = None
        if not USE_SERVICE_ACCOUNTS:
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', self.__OAUTH_SCOPE)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            else:
                LOGGER.error("The token.json file is missing")
        else:
            LOGGER.info(f"Authorizing with {SERVICE_ACCOUNT_INDEX}.json file")
            creds = service_account.Credentials.from_service_account_file(
                f'accounts/{SERVICE_ACCOUNT_INDEX}.json', scopes=self.__OAUTH_SCOPE)
        return build('drive', 'v3', credentials=creds, cache_discovery=False)

    def alt_authorize(self):
        creds = None
        if USE_SERVICE_ACCOUNTS and not self.alt_auth:
            self.alt_auth = True
            if os.path.exists('token.json'):
                LOGGER.info("Authorizing with token.json file")
                creds = Credentials.from_authorized_user_file('token.json', self.__OAUTH_SCOPE)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                return build('drive', 'v3', credentials=creds, cache_discovery=False)
            else:
                LOGGER.error("The token.json file is missing")
        return None

    @staticmethod
    def getIdFromUrl(link: str):
        if "folders" in link or "file" in link:
            regex = r'https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)'
            res = re.search(regex, link)
            if res is None:
                raise IndexError("Drive ID not found")
            return res.group(3)
        parsed = urlparse(link)
        return parse_qs(parsed.query)['id'][0]

    def deleteFile(self, link: str):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg
        msg = ''
        try:
            res = self.__service.files().delete(
                      fileId=file_id,
                      supportsAllDrives=IS_TEAM_DRIVE).execute()
            msg = "Permanently deleted"
        except HttpError as err:
            if "File not found" in str(err):
                msg = "File not found"
            elif "insufficientFilePermissions" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.deleteFile(link)
                msg = "Insufficient file permissions"
            else:
                msg = str(err)
            LOGGER.error(msg)
        return msg

    def switchServiceAccount(self):
        global SERVICE_ACCOUNT_INDEX
        service_account_count = len(os.listdir("accounts"))
        if SERVICE_ACCOUNT_INDEX == service_account_count - 1:
            SERVICE_ACCOUNT_INDEX = 0
        self.sa_count += 1
        SERVICE_ACCOUNT_INDEX += 1
        LOGGER.info(f"Authorizing with {SERVICE_ACCOUNT_INDEX}.json file")
        self.__service = self.authorize()

    def __set_permission_public(self, file_id):
        permissions = {
            'type': 'anyone',
            'role': 'reader'
        }
        return self.__service.permissions().create(
                   supportsAllDrives=True,
                   fileId=file_id,
                   body=permissions).execute()

    def __set_permission_email(self, file_id, email):
        permissions = {
            'type': 'user',
            'role': 'reader',
            'emailAddress': email
        }
        return self.__service.permissions().create(
                   supportsAllDrives=True,
                   fileId=file_id,
                   body=permissions,
                   sendNotificationEmail=False).execute()

    def setPerm(self, link, access):
        try:
            file_id = self.getIdFromUrl(link)
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
            LOGGER.error(err)
            if "File not found" in str(err):
                msg = "File not found"
            elif "insufficientFilePermissions" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.setPerm(link, access)
                msg = "Insufficient file permissions"
            else:
                msg = str(err)
        return msg

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError),
           before=before_log(LOGGER, logging.DEBUG))
    def copyFile(self, file_id, dest_id):
        body = {
            'parents': [dest_id]
        }
        try:
            res = self.__service.files().copy(
                      supportsAllDrives=True,
                      fileId=file_id,
                      body=body).execute()
            return res
        except HttpError as err:
            if err.resp.get('content-type', '').startswith('application/json'):
                reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                if reason in ['userRateLimitExceeded', 'dailyLimitExceeded']:
                    if USE_SERVICE_ACCOUNTS:
                        if self.sa_count == len(os.listdir("accounts")) or self.sa_count > 50:
                            self.is_cancelled = True
                            raise err
                        else:
                            self.switchServiceAccount()
                            return self.copyFile(file_id, dest_id)
                    else:
                        self.is_cancelled = True
                        LOGGER.info(f"Warning: {reason}")
                        raise err
                else:
                    raise err

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError),
           before=before_log(LOGGER, logging.DEBUG))
    def getFileMetadata(self, file_id):
        return self.__service.files().get(
                   supportsAllDrives=True,
                   fileId=file_id,
                   fields='name, id, mimeType, size').execute()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError),
           before=before_log(LOGGER, logging.DEBUG))
    def getFilesByFolderId(self, folder_id):
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
                           fields='nextPageToken, files(id, name, mimeType, size)',
                           pageToken=page_token).execute()
            for file in response.get('files', []):
                files.append(file)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return files

    def clone(self, link, key):
        self.is_cloning = True
        self.start_time = time.time()
        self.total_files = 0
        self.total_folders = 0
        parent_id = PARENT_ID
        index_url = INDEX_URL
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg
        if key in DEST_DRIVES:
            parent_id = DEST_DRIVES[key][0]
            try:
                index_url = DEST_DRIVES[key][1]
            except IndexError:
                index_url = None
        msg = ""
        try:
            meta = self.getFileMetadata(file_id)
            name = meta.get("name")
            mime_type = meta.get("mimeType")
            if mime_type == self.__G_DRIVE_DIR_MIME_TYPE:
                dir_id = self.create_directory(meta.get('name'), parent_id)
                self.cloneFolder(meta.get('name'), meta.get('name'), meta.get('id'), dir_id)
                durl = self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)
                if self.is_cancelled:
                    LOGGER.info(f"Deleting cloned data from Drive")
                    self.deleteFile(durl)
                    return "The clone task has been cancelled"
                msg += f'<b>Name:</b> <code>{name}</code>'
                msg += f'\n<b>Size:</b> {get_readable_file_size(self.transferred_size)}'
                msg += f'\n<b>Type:</b> Folder'
                msg += f'\n<b>SubFolders:</b> {self.total_folders}'
                msg += f'\n<b>Files:</b> {self.total_files}'
                msg += f'\n\n<b><a href="{self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)}">Drive Link</a></b>'
                if index_url is not None:
                    url_path = requests.utils.quote(f'{meta.get("name")}', safe='')
                    url = f'{index_url}/{url_path}/'
                    msg += f'<b> | <a href="{url}">Index Link</a></b>'
            else:
                file = self.copyFile(meta.get('id'), parent_id)
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
            LOGGER.error(err)
            if "User rate limit exceeded" in str(err):
                msg = "User rate limit exceeded"
            elif "File not found" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.clone(link, key)
                msg = "File not found"
            else:
                msg = str(err)
        return msg

    def cloneFolder(self, name, local_path, folder_id, parent_id):
        files = self.getFilesByFolderId(folder_id)
        if len(files) == 0:
            return parent_id
        for file in files:
            if file.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                self.total_folders += 1
                file_path = os.path.join(local_path, file.get('name'))
                current_dir_id = self.create_directory(file.get('name'), parent_id)
                self.cloneFolder(file.get('name'), file_path, file.get('id'), current_dir_id)
            else:
                self.total_files += 1
                self.transferred_size += int(file.get('size', 0))
                self.copyFile(file.get('id'), parent_id)
            if self.is_cancelled:
                break

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError),
           before=before_log(LOGGER, logging.DEBUG))
    def create_directory(self, directory_name, parent_id):
        file_metadata = {
            "name": directory_name,
            "mimeType": self.__G_DRIVE_DIR_MIME_TYPE
        }
        if parent_id is not None:
            file_metadata["parents"] = [parent_id]
        file = self.__service.files().create(
                   supportsAllDrives=True,
                   body=file_metadata).execute()
        file_id = file.get("id")
        if not IS_TEAM_DRIVE:
            self.__set_permission_public(file_id)
        return file_id

    def count(self, link):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg
        msg = ""
        try:
            meta = self.getFileMetadata(file_id)
            mime_type = meta.get('mimeType')
            if mime_type == self.__G_DRIVE_DIR_MIME_TYPE:
                self.gDrive_directory(meta)
                msg += f'<b>Name:</b> <code>{meta.get("name")}</code>'
                msg += f'\n<b>Size:</b> {get_readable_file_size(self.total_bytes)}'
                msg += f'\n<b>Type:</b> Folder'
                msg += f'\n<b>SubFolders:</b> {self.total_folders}'
            else:
                msg += f'<b>Name: </b><code>{meta.get("name")}</code>'
                if mime_type is None:
                    mime_type = 'File'
                self.total_files += 1
                self.gDrive_file(meta)
                msg += f'\n<b>Size:</b> {get_readable_file_size(self.total_bytes)}'
                msg += f'\n<b>Type:</b> {mime_type}'
            msg += f'\n<b>Files:</b> {self.total_files}'
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            LOGGER.error(err)
            if "File not found" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.count(link)
                msg = "File not found"
            else:
                msg = str(err)
        return msg

    def gDrive_file(self, filee):
        size = int(filee.get('size', 0))
        self.total_bytes += size

    def gDrive_directory(self, drive_folder):
        files = self.getFilesByFolderId(drive_folder['id'])
        if len(files) == 0:
            return
        for filee in files:
            shortcut_details = filee.get('shortcutDetails')
            if shortcut_details is not None:
                mime_type = shortcut_details['targetMimeType']
                file_id = shortcut_details['targetId']
                filee = self.getFileMetadata(file_id)
            else:
                mime_type = filee.get('mimeType')
            if mime_type == self.__G_DRIVE_DIR_MIME_TYPE:
                self.total_folders += 1
                self.gDrive_directory(filee)
            else:
                self.total_files += 1
                self.gDrive_file(filee)

    def helper(self, link):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(msg)
            return msg, "", "", ""
        try:
            meta = self.getFileMetadata(file_id)
            name = meta.get('name')
            if meta.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                self.gDrive_directory(meta)
            else:
                self.total_files += 1
                self.gDrive_file(meta)
            size = self.total_bytes
            files = self.total_files
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            LOGGER.error(err)
            if "File not found" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.helper(link)
                msg = "File not found"
            else:
                msg = str(err)
            return msg, "", "", ""
        return "", size, name, files

    def escapes(self, str_val):
        chars = ['\\', "'", '"', r'\a', r'\b', r'\f', r'\n', r'\r', r'\t']
        for char in chars:
            str_val = str_val.replace(char, '\\' + char)
        return str_val

    def receive_callback(self, request_id, response, exception):
        # request_id = order number of request = shared drive index (1 based)
        if exception is not None:
            exception = str(exception).replace('>', '').replace('<', '')
            LOGGER.error(str(exception))
        else: 
            if response['files']:
                self.response[request_id] = response

    def drive_query(self, DRIVE_IDS, search_type, file_name):
        batch = self.__service.new_batch_http_request(self.receive_callback)
        query = f"name contains '{file_name}' and "
        if search_type is not None:
            if search_type == '-d':
                query += "mimeType = 'application/vnd.google-apps.folder' and "
            elif search_type == '-f':
                query += "mimeType != 'application/vnd.google-apps.folder' and "
        query += "trashed=false"
        for parent_id in DRIVE_IDS:
            if parent_id == "root":
                batch.add(
                    self.__service.files().list(
                        q=query + " and 'me' in owners",
                        pageSize=1000,
                        spaces='drive',
                        fields='files(id, name, mimeType, size)',
                        orderBy='folder, modifiedTime desc'))
            else:
                batch.add(
                    self.__service.files().list(
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        driveId=parent_id,
                        q=query,
                        corpora='drive',
                        spaces='drive',
                        pageSize=1000,
                        fields='files(id, name, mimeType, size)',
                        orderBy='folder, modifiedTime desc'))
        batch.execute()

    def drive_list(self, file_name):
        file_name = self.escapes(file_name)
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
        token_service = self.alt_authorize()
        if token_service is not None:
            self.__service = token_service
        self.drive_query(DRIVE_IDS, search_type, file_name)
        add_title_msg = True
        for files in self.response:
            index = int(files) - 1
            if add_title_msg:
                msg = f'<h4>Query: {file_name}</h4><br>'
                add_title_msg = False
            msg += f"╾────────────╼<br><b>{DRIVE_NAMES[index]}</b><br>╾────────────╼<br>"
            # Detect whether the current entity is a folder or file
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
                self.telegraph_content[i] += f'<b><a href="https://telegra.ph/{self.path[i-1]}">Previous</a>' \
                                             f' | Page {i+1}/{total_pages}</b>'
            else:
                self.telegraph_content[i] += f'<b>Page {i+1}/{total_pages}</b>'

            self.create_page(
                TELEGRAPH[acc_no],
                self.telegraph_content[i])

            if i != 0:
                # Edit previous page to add next page link
                self.telegraph_content[i-1] += f'<b> | <a href="https://telegra.ph/{self.path[i]}">Next</a></b>'

                self.edit_page(
                    TELEGRAPH[(acc_no - 1) if i % page_per_acc == 0 else acc_no],
                    self.telegraph_content[i-1],
                    self.path[i-1])

        msg = f"<b>Found {response_count} results matching '{file_name}' in {len(DRIVE_IDS)} Drives</b> " \
              f"<b>(Time taken {round(time.time() - start_time, 2)}s)</b>"
        button = ButtonMaker()
        button.build_button("VIEW RESULTS 🗂️", f"https://telegra.ph/{self.path[0]}")
        return msg, InlineKeyboardMarkup(button.build_menu(1))

    def create_page(self, acc, content):
        try:
            self.path.append(
                acc.create_page(
                    title=self.title,
                    author_name=self.author_name,
                    author_url=self.author_url,
                    html_content=content)['path'])
        except RetryAfterError as e:
            LOGGER.info(f"Cooldown: {e.retry_after} seconds")
            time.sleep(e.retry_after)
            self.create_page(acc, content)

    def edit_page(self, acc, content, path):
        try:
            acc.edit_page(
                path=path,
                title=self.title,
                author_name=self.author_name,
                author_url=self.author_url,
                html_content=content)
        except RetryAfterError as e:
            LOGGER.info(f"Cooldown: {e.retry_after} seconds")
            time.sleep(e.retry_after)
            self.edit_page(acc, content, path)

    def upload(self, file_name: str):
        self.is_downloading = False
        self.is_uploading = True
        file_dir = f"{DOWNLOAD_DIR}{self.__listener.message.message_id}"
        file_path = f"{file_dir}/{file_name}"
        size = get_readable_file_size(get_path_size(file_path))
        self.updater = SetInterval(self.update_interval, self._on_upload_progress)
        try:
            if os.path.isfile(file_path):
                mime_type = get_mime_type(file_path)
                link = self.upload_file(file_path, file_name, mime_type, PARENT_ID)
                if self.is_cancelled:
                    return
                if link is None:
                    raise Exception("The upload task has been manually cancelled")
            else:
                mime_type = 'Folder'
                dir_id = self.create_directory(os.path.basename(os.path.abspath(file_name)), PARENT_ID)
                result = self.upload_dir(file_path, dir_id)
                if result is None:
                    raise Exception("The upload task has been manually cancelled")
                link = f"https://drive.google.com/folderview?id={dir_id}"
                if self.is_cancelled:
                    return
        except Exception as e:
            if isinstance(e, RetryError):
                LOGGER.info(f"Total attempts: {e.last_attempt.attempt_number}")
                err = e.last_attempt.exception()
            else:
                err = e
            LOGGER.error(err)
            self.__listener.onUploadError(str(err))
            self.is_errored = True
        finally:
            self.updater.cancel()
            if self.is_cancelled and not self.is_errored:
                if mime_type == 'Folder':
                    LOGGER.info("Deleting uploaded data from Drive")
                    link = f"https://drive.google.com/folderview?id={dir_id}"
                    self.deleteFile(link)
                return
            elif self.is_errored:
                return
        self.__listener.onUploadComplete(link, size, self.total_files, self.total_folders, mime_type, self.name)

    def upload_dir(self, input_directory, parent_id):
        list_dirs = os.listdir(input_directory)
        if len(list_dirs) == 0:
            return parent_id
        new_id = None
        for item in list_dirs:
            current_file_name = os.path.join(input_directory, item)
            if os.path.isdir(current_file_name):
                current_dir_id = self.create_directory(item, parent_id)
                new_id = self.upload_dir(current_file_name, current_dir_id)
                self.total_folders += 1
            else:
                mime_type = get_mime_type(current_file_name)
                file_name = current_file_name.split("/")[-1]
                # 'current_file_name' will have the full path
                self.upload_file(current_file_name, file_name, mime_type, parent_id)
                self.total_files += 1
                new_id = parent_id
            if self.is_cancelled:
                break
        return new_id

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=(retry_if_exception_type(HttpError) | retry_if_exception_type(IOError)),
           before=before_log(LOGGER, logging.DEBUG))
    def upload_file(self, file_path, file_name, mime_type, parent_id):
        file_metadata = {
            'name': file_name,
            'mimeType': mime_type
        }
        if parent_id is not None:
            file_metadata['parents'] = [parent_id]
        if os.path.getsize(file_path) == 0:
            media_body = MediaFileUpload(file_path, mimetype=mime_type, resumable=False)
            response = self.__service.files().create(
                           supportsAllDrives=True,
                           body=file_metadata,
                           media_body=media_body).execute()
            if not IS_TEAM_DRIVE:
                self.__set_permission_public(response['id'])
            drive_file = self.__service.files().get(
                             supportsAllDrives=True,
                             fileId=response['id']).execute()
            download_url = self.__G_DRIVE_BASE_DOWNLOAD_URL.format(drive_file.get('id'))
            return download_url
        media_body = MediaFileUpload(file_path, mimetype=mime_type, resumable=True,
                                     chunksize=50 * 1024 * 1024)
        drive_file = self.__service.files().create(
                         supportsAllDrives=True,
                         body=file_metadata,
                         media_body=media_body)
        response = None
        while response is None:
            if self.is_cancelled:
                break
            try:
                self.status, response = drive_file.next_chunk()
            except HttpError as err:
                if err.resp.get('content-type', '').startswith('application/json'):
                    reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                    if reason not in ['userRateLimitExceeded', 'dailyLimitExceeded']:
                        raise err
                    if USE_SERVICE_ACCOUNTS:
                        self.switchServiceAccount()
                        return self.upload_file(file_path, file_name, mime_type, parent_id)
                    else:
                        LOGGER.error(f"Warning: {reason}")
                        raise err
        if self.is_cancelled:
            return
        self._file_uploaded_bytes = 0
        if not IS_TEAM_DRIVE:
            self.__set_permission_public(response['id'])
        drive_file = self.__service.files().get(
                         supportsAllDrives=True,
                         fileId=response['id']).execute()
        download_url = self.__G_DRIVE_BASE_DOWNLOAD_URL.format(drive_file.get('id'))
        return download_url

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError),
           before=before_log(LOGGER, logging.DEBUG))
    def _on_upload_progress(self):
        if self.status is not None:
            chunk_size = self.status.total_size * self.status.progress() - self._file_uploaded_bytes
            self._file_uploaded_bytes = self.status.total_size * self.status.progress()
            self.uploaded_bytes += chunk_size
            self.total_time += self.update_interval

    def download(self, link):
        self.is_downloading = True
        file_id = self.getIdFromUrl(link)
        self.updater = SetInterval(self.update_interval, self._on_download_progress)
        try:
            meta = self.getFileMetadata(file_id)
            path = f"{DOWNLOAD_DIR}{self.__listener.uid}/"
            if meta.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
                self.download_folder(file_id, path, meta.get('name'))
            else:
                os.makedirs(path)
                self.download_file(file_id, path, meta.get('name'), meta.get('mimeType'))
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            LOGGER.error(err)
            if "downloadQuotaExceeded" in str(err):
                err = "Download quota exceeded."
            elif "File not found" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    self.updater.cancel()
                    return self.download(link)
            self.__listener.onDownloadError(err)
            self.is_cancelled = True
        finally:
            self.updater.cancel()
            if self.is_cancelled:
                return
        self.__listener.onDownloadComplete()

    def download_folder(self, folder_id, path, folder_name):
        folder_name = folder_name.replace('/', '')
        if not os.path.exists(path + folder_name):
            os.makedirs(path + folder_name)
        path += folder_name + '/'
        result = self.getFilesByFolderId(folder_id)
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
                self.download_folder(file_id, path, filename)
            elif not os.path.isfile(path + filename):
                self.download_file(file_id, path, filename, mime_type)
            if self.is_cancelled:
                break

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=(retry_if_exception_type(HttpError) | retry_if_exception_type(IOError)),
           before=before_log(LOGGER, logging.DEBUG))
    def download_file(self, file_id, path, filename, mime_type):
        request = self.__service.files().get_media(fileId=file_id)
        filename = filename.replace('/', '')
        fh = FileIO('{}{}'.format(path, filename), 'wb')
        downloader = MediaIoBaseDownload(fh, request, chunksize=50 * 1024 * 1024)
        done = False
        while not done:
            if self.is_cancelled:
                fh.close()
                break
            try:
                self.dstatus, done = downloader.next_chunk()
            except HttpError as err:
                if err.resp.get('content-type', '').startswith('application/json'):
                    reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                    if reason not in ['downloadQuotaExceeded', 'dailyLimitExceeded']:
                        raise err
                    if USE_SERVICE_ACCOUNTS:
                        if self.sa_count == len(os.listdir("accounts")) or self.sa_count > 50:
                            self.is_cancelled = True
                            raise err
                        else:
                            self.switchServiceAccount()
                            return self.download_file(file_id, path, filename, mime_type)
                    else:
                        LOGGER.error(f"Warning: {reason}")
                        raise err
        self._file_downloaded_bytes = 0

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6),
           stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError),
           before=before_log(LOGGER, logging.DEBUG))
    def _on_download_progress(self):
        if self.dstatus is not None:
            chunk_size = self.dstatus.total_size * self.dstatus.progress() - self._file_downloaded_bytes
            self._file_downloaded_bytes = self.dstatus.total_size * self.dstatus.progress()
            self.downloaded_bytes += chunk_size
            self.dtotal_time += self.update_interval

    def cancel_task(self):
        self.is_cancelled = True
        if self.is_downloading:
            LOGGER.info(f"Cancelling download: {self.name}")
            self.__listener.onDownloadError("The download task has been cancelled")
        elif self.is_cloning:
            LOGGER.info(f"Cancelling clone: {self.name}")
        elif self.is_uploading:
            LOGGER.info(f"Cancelling upload: {self.name}")
            self.__listener.onUploadError("The upload task has been cancelled")
