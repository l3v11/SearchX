import logging
import os
import json
import re
import requests
import time

import urllib.parse as urlparse
from urllib.parse import parse_qs
from random import randrange
from tenacity import retry, wait_exponential, stop_after_attempt, \
    retry_if_exception_type, before_log, RetryError
from timeit import default_timer as timer

from telegram import InlineKeyboardMarkup
from telegraph.exceptions import RetryAfterError

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from bot import LOGGER, DRIVE_NAMES, DRIVE_IDS, INDEX_URLS, parent_id, \
    IS_TEAM_DRIVE, telegraph, USE_SERVICE_ACCOUNTS, INDEX_URL
from bot.helper.ext_utils.bot_utils import *
from bot.helper.telegram_helper.button_builder import ButtonMaker

logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

if USE_SERVICE_ACCOUNTS:
    SERVICE_ACCOUNT_INDEX = randrange(len(os.listdir("accounts")))

telegraph_limit = 60

class GoogleDriveHelper:
    def __init__(self, name=None):
        # Check https://developers.google.com/drive/scopes for all available scopes
        self.__OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__G_DRIVE_BASE_DOWNLOAD_URL = "https://drive.google.com/uc?id={}&export=download"
        self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self.__service = self.authorize()
        self.batch_dict = {}
        self.telegraph_content = []
        self.path = []
        self.start_time = 0
        self.is_cancelled = False
        self.name = name
        self.total_bytes = 0
        self.total_files = 0
        self.total_folders = 0
        self.transferred_size = 0
        self.__sa_count = 0
        self.alt_auth = False

    def cspeed(self):
        try:
            return self.transferred_size / int(time.time() - self.start_time)
        except ZeroDivisionError:
            return 0

    def authorize(self):
        creds = None
        if not USE_SERVICE_ACCOUNTS:
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', self.__OAUTH_SCOPE)
            else:
                LOGGER.error("token.json file is missing")
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
                return build('drive', 'v3', credentials=creds, cache_discovery=False)
        return None

    @staticmethod
    def getIdFromUrl(link: str):
        if "folders" in link or "file" in link:
            regex = r"https://drive\.google\.com/(drive)?/?u?/?\d?/?(mobile)?/?(file)?(folders)?/?d?/([-\w]+)[?+]?/?(w+)?"
            res = re.search(regex, link)
            if res is None:
                raise IndexError("Drive ID not found")
            return res.group(5)
        parsed = urlparse.urlparse(link)
        return parse_qs(parsed.query)['id'][0]

    def deleteFile(self, link: str):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(f"{msg}")
            return msg
        msg = ''
        try:
            res = self.__service.files().delete(fileId=file_id, supportsTeamDrives=IS_TEAM_DRIVE).execute()
            msg += "Permanently deleted"
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
            LOGGER.error(f"{msg}")
        return msg

    def switchServiceAccount(self):
        global SERVICE_ACCOUNT_INDEX
        service_account_count = len(os.listdir("accounts"))
        if SERVICE_ACCOUNT_INDEX == service_account_count - 1:
            SERVICE_ACCOUNT_INDEX = 0
        self.__sa_count += 1
        SERVICE_ACCOUNT_INDEX += 1
        LOGGER.info(f"Authorizing with {SERVICE_ACCOUNT_INDEX}.json file")
        self.__service = self.authorize()

    def __set_permission_public(self, file_id):
        permissions = {
            'type': 'anyone',
            'role': 'reader'
        }
        return self.__service.permissions().create(supportsTeamDrives=True, fileId=file_id,
                                                   body=permissions).execute()

    def __set_permission_email(self, file_id, email):
        permissions = {
            'type': 'user',
            'role': 'reader',
            'emailAddress': email
        }
        return self.__service.permissions().create(supportsTeamDrives=True, fileId=file_id,
                                                   body=permissions, sendNotificationEmail=False).execute()

    def setPerm(self, link, access):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(f"{msg}")
            return msg
        msg = ''
        try:
            if access != "anyone":
                self.__set_permission_email(file_id, access)
                msg += f"Added <code>{access}</code> as viewer"
            else:
                self.__set_permission_public(file_id)
                msg += "Set permission to <code>Anyone with the link</code>"
        except HttpError as err:
            err = str(err).replace('>', '').replace('<', '')
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
            LOGGER.error(f"{msg}")
        return msg

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def copyFile(self, file_id, dest_id):
        body = {
            'parents': [dest_id]
        }
        try:
            res = self.__service.files().copy(supportsAllDrives=True, fileId=file_id, body=body).execute()
            return res
        except HttpError as err:
            if err.resp.get('content-type', '').startswith('application/json'):
                reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
                if reason in ['userRateLimitExceeded', 'dailyLimitExceeded']:
                    if USE_SERVICE_ACCOUNTS:
                        if self.__sa_count == len(os.listdir("accounts")) or self.__sa_count > 50:
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

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def getFileMetadata(self, file_id):
        return self.__service.files().get(supportsAllDrives=True, fileId=file_id,
                                          fields="name, id, mimeType, size").execute()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def getFilesByFolderId(self, folder_id):
        page_token = None
        query = f"'{folder_id}' in parents and trashed = false"
        files = []
        while True:
            response = self.__service.files().list(supportsTeamDrives=True,
                                                   includeTeamDriveItems=True,
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

    def clone(self, link):
        self.start_time = time.time()
        self.total_files = 0
        self.total_folders = 0
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(f"{msg}")
            return msg
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
                    LOGGER.info(f"Deleting: {name}")
                    self.deleteFile(durl)
                    return "The task has been cancelled"
                msg += f'<b>Name:</b> <code>{name}</code>'
                msg += f'\n<b>Size:</b> {get_readable_file_size(self.transferred_size)}'
                msg += f'\n<b>Type:</b> Folder'
                msg += f'\n<b>SubFolders:</b> {self.total_folders}'
                msg += f'\n<b>Files:</b> {self.total_files}'
                msg += f'\n\n<b><a href="{self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)}">Drive Link</a></b>'
                if INDEX_URL is not None:
                    url_path = requests.utils.quote(f'{meta.get("name")}', safe='')
                    url = f'{INDEX_URL}/{url_path}/'
                    msg += f'<b> | <a href="{url}">Index Link</a></b>'
            else:
                file = self.copyFile(meta.get('id'), parent_id)
                msg += f'<b>Name:</b> <code>{file.get("name")}</code>'
                if mime_type is None:
                    mime_type = 'File'
                msg += f'\n<b>Size:</b> {get_readable_file_size(int(meta.get("size", 0)))}'
                msg += f'\n<b>Type:</b> {mime_type}'
                msg += f'\n\n<b><a href="{self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get("id"))}">Drive Link</a></b>'
                if INDEX_URL is not None:
                    url_path = requests.utils.quote(f'{file.get("name")}', safe='')
                    url = f'{INDEX_URL}/{url_path}'
                    msg += f'<b> | <a href="{url}">Index Link</a></b>'
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            if "User rate limit exceeded" in str(err):
                msg = "User rate limit exceeded"
            elif "File not found" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.clone(link)
                msg = "File not found"
            else:
                msg = str(err)
            LOGGER.error(msg)
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

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def create_directory(self, directory_name, parent_id):
        file_metadata = {
            "name": directory_name,
            "mimeType": self.__G_DRIVE_DIR_MIME_TYPE
        }
        if parent_id is not None:
            file_metadata["parents"] = [parent_id]
        file = self.__service.files().create(supportsTeamDrives=True, body=file_metadata).execute()
        file_id = file.get("id")
        if not IS_TEAM_DRIVE:
            self.__set_permission_public(file_id)
        return file_id

    def count(self, link):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            LOGGER.error(f"{msg}")
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
            if "File not found" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.count(link)
                msg = "File not found"
            else:
                msg = str(err)
            LOGGER.error(msg)
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
            LOGGER.info(f"Checking: {name}")
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
            if "File not found" in str(err):
                token_service = self.alt_authorize()
                if token_service is not None:
                    self.__service = token_service
                    return self.helper(link)
                msg = "File not found"
            else:
                msg = str(err)
            LOGGER.error(msg)
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
                self.batch_dict[request_id] = response

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
                batch.add(self.__service.files().list(
                              q=query + " and 'me' in owners",
                              pageSize=1000,
                              spaces='drive',
                              fields='files(id, name, mimeType, size, parents)',
                              orderBy='folder, modifiedTime desc'))
            else:
                batch.add(self.__service.files().list(
                              supportsTeamDrives=True,
                              includeTeamDriveItems=True,
                              teamDriveId=parent_id,
                              q=query,
                              corpora='drive',
                              spaces='drive',
                              pageSize=1000,
                              fields='files(id, name, mimeType, size, teamDriveId, parents)',
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
        content_count = 0
        token_service = self.alt_authorize()
        if token_service is not None:
            self.__service = token_service
        start = timer()
        response = self.drive_query(DRIVE_IDS, search_type, file_name)
        end = timer()
        time_taken = round(end-start, 2)
        response_dict = self.batch_dict
        add_title_msg = True
        if response_dict:
            for files in response_dict:
                index = int(files) - 1
                if add_title_msg:
                    msg = f'<h4>Query: {file_name}</h4><br>'
                    add_title_msg = False
                msg += f"╾────────────╼<br><b>{DRIVE_NAMES[index]}</b><br>╾────────────╼<br>"
                # Detect whether current entity is a folder or file
                for file in response_dict[files]["files"]:
                    if file.get('mimeType') == "application/vnd.google-apps.folder":
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
                    content_count += 1
                    response_count += 1
                    if content_count == telegraph_limit:
                        self.telegraph_content.append(msg)
                        msg = ""
                        content_count = 0

        if msg != '':
            self.telegraph_content.append(msg)
        total_pages = len(self.telegraph_content)
        if total_pages == 0:
            return "<b>Found nothing :(</b>", None

        for i in range(total_pages):
            if i % page_per_acc == 0:
                acc_no = (acc_no+1) % len(telegraph)
            if i != 0:
                # Add previous page link
                self.telegraph_content[i] += f'<b><a href="https://telegra.ph/{self.path[i-1]}">Previous</a> | Page {i+1}/{total_pages}</b>'
            else:
                self.telegraph_content[i] += f'<b>Page {i+1}/{total_pages}</b>'

            try:
                self.path.append(
                    telegraph[acc_no].create_page(title='SearchX',
                                                  author_name='Levi',
                                                  author_url='https://t.me/l3v11',
                                                  html_content=self.telegraph_content[i])['path'])
            except RetryAfterError as e:
                LOGGER.info(f"Cooldown: {e.retry_after} seconds")
                time.sleep(e.retry_after)
                self.path.append(
                    telegraph[acc_no].create_page(title='SearchX',
                                                  author_name='Levi',
                                                  author_url='https://t.me/l3v11',
                                                  html_content=self.telegraph_content[i])['path'])

            if i != 0:
                # Edit previous page to add next page link
                self.telegraph_content[i-1] += f'<b> | <a href="https://telegra.ph/{self.path[i]}">Next</a></b>'
                try:
                    telegraph[(acc_no-1) if i % page_per_acc == 0 else acc_no].edit_page(path=self.path[i-1],
                                              title='SearchX',
                                              author_name='Levi',
                                              author_url='https://t.me/l3v11',
                                              html_content=self.telegraph_content[i-1])
                except RetryAfterError as e:
                    LOGGER.info(f"Cooldown: {e.retry_after} seconds")
                    time.sleep(e.retry_after)
                    telegraph[(acc_no-1) if i % page_per_acc == 0 else acc_no].edit_page(path=self.path[i-1],
                                              title='SearchX',
                                              author_name='Levi',
                                              author_url='https://t.me/l3v11',
                                              html_content=self.telegraph_content[i-1])

        msg = f"<b>Found {response_count} results matching '{file_name}' in {len(DRIVE_IDS)} Drives</b> " \
              f"<b>(Time taken {time_taken}s)</b>"
        buttons = ButtonMaker()
        buttons.build_button("VIEW RESULTS 🗂️", f"https://telegra.ph/{self.path[0]}")
        return msg, InlineKeyboardMarkup(buttons.build_menu(1))

    def cancel_task(self):
        self.is_cancelled = True
        LOGGER.info(f"Cancelling: {self.name}")
