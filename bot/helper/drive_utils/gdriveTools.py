import logging
import os
import json
import re
import requests

import urllib.parse as urlparse
from urllib.parse import parse_qs
from random import randrange

from telegram import InlineKeyboardMarkup

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import *

from bot import LOGGER, DRIVE_NAME, DRIVE_ID, INDEX_URL, telegra_ph, \
    IS_TEAM_DRIVE, parent_id, USE_SERVICE_ACCOUNTS, DRIVE_INDEX_URL
from bot.helper.ext_utils.bot_utils import *
from bot.helper.telegram_helper import button_builder

logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

if USE_SERVICE_ACCOUNTS:
    SERVICE_ACCOUNT_INDEX = randrange(len(os.listdir("accounts")))

telegraph_limit = 95

class GoogleDriveHelper:
    def __init__(self, name=None, listener=None):
        self.listener = listener
        self.name = name
        self.__G_DRIVE_TOKEN_FILE = "token.json"
        # Check https://developers.google.com/drive/scopes for all available scopes
        self.__OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']
        self.__G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.__G_DRIVE_BASE_DOWNLOAD_URL = "https://drive.google.com/uc?id={}&export=download"
        self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self.__service = self.authorize()
        self.telegraph_content = []
        self.path = []
        self.total_bytes = 0
        self.total_files = 0
        self.total_folders = 0
        self.transferred_size = 0

    def authorize(self):
        # Get credentials
        credentials = None
        if not USE_SERVICE_ACCOUNTS:
            if os.path.exists(self.__G_DRIVE_TOKEN_FILE):
                credentials = Credentials.from_authorized_user_file(self.__G_DRIVE_TOKEN_FILE, self.__OAUTH_SCOPE)
            if credentials is None or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
        else:
            LOGGER.info(f"Using SA file: {SERVICE_ACCOUNT_INDEX}.json")
            credentials = service_account.Credentials.from_service_account_file(
                f'accounts/{SERVICE_ACCOUNT_INDEX}.json', scopes=self.__OAUTH_SCOPE)
        return build('drive', 'v3', credentials=credentials, cache_discovery=False)

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

    def deletefile(self, link: str):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            return msg
        msg = ''
        LOGGER.info(f"Deleting: {file_id}")
        try:
            res = self.__service.files().delete(fileId=file_id, supportsTeamDrives=IS_TEAM_DRIVE).execute()
            msg = "Successfully deleted"
            LOGGER.info(f"{msg}")
        except HttpError as err:
            if "File not found" in str(err):
                msg = "No such file exists"
            elif "insufficientFilePermissions" in str(err):
                msg = "Insufficient file permissions"
            else:
                msg = str(err)
            LOGGER.error(f"{msg}")
        finally:
            return msg

    def switchServiceAccount(self):
        global SERVICE_ACCOUNT_INDEX
        service_account_count = len(os.listdir("accounts"))
        if SERVICE_ACCOUNT_INDEX == service_account_count - 1:
            SERVICE_ACCOUNT_INDEX = 0
        SERVICE_ACCOUNT_INDEX += 1
        LOGGER.info(f"Using SA file: {SERVICE_ACCOUNT_INDEX}.json")
        self.__service = self.authorize()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def __set_permission(self, drive_id):
        permissions = {
            'role': 'reader',
            'type': 'anyone',
            'value': None,
            'withLink': True
        }
        return self.__service.permissions().create(supportsTeamDrives=True, fileId=drive_id,
                                                   body=permissions).execute()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
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
                if reason == 'userRateLimitExceeded' or reason == 'dailyLimitExceeded':
                    if USE_SERVICE_ACCOUNTS:
                        self.switchServiceAccount()
                        return self.copyFile(file_id, dest_id)
                    else:
                        LOGGER.info(f"Warning: {reason}")
                        raise err
                else:
                    raise err

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
           retry=retry_if_exception_type(HttpError), before=before_log(LOGGER, logging.DEBUG))
    def getFileMetadata(self, file_id):
        return self.__service.files().get(supportsAllDrives=True, fileId=file_id,
                                              fields="name, id, mimeType, size").execute()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
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
        self.transferred_size = 0
        self.total_files = 0
        self.total_folders = 0
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            return msg
        msg = ""
        LOGGER.info(f"Cloning: {file_id}")
        try:
            meta = self.getFileMetadata(file_id)
            if meta.get("mimeType") == self.__G_DRIVE_DIR_MIME_TYPE:
                dir_id = self.create_directory(meta.get('name'), parent_id)
                result = self.cloneFolder(meta.get('name'), meta.get('name'), meta.get('id'), dir_id)
                msg += f'<b>Filename: </b><code>{meta.get("name")}</code>'
                msg += f'\n<b>Size: </b>{get_readable_file_size(self.transferred_size)}'
                msg += f"\n<b>Type: </b>Folder"
                msg += f"\n<b>SubFolders: </b>{self.total_folders}"
                msg += f"\n<b>Files: </b>{self.total_files}"
                msg += f'\n\n<a href="{self.__G_DRIVE_DIR_BASE_DOWNLOAD_URL.format(dir_id)}">Drive Link</a>'
                if DRIVE_INDEX_URL is not None:
                    url = requests.utils.requote_uri(f'{DRIVE_INDEX_URL}/{meta.get("name")}/')
                    msg += f' | <a href="{url}">Index Link</a>'
            else:
                file = self.copyFile(meta.get('id'), parent_id)
                try:
                    typ = file.get('mimeType')
                except:
                    typ = 'File' 
                msg += f'<b>Filename: </b><code>{file.get("name")}</code>'
                try:
                    msg += f'\n<b>Size: </b>{get_readable_file_size(int(meta.get("size")))}'
                    msg += f'\n<b>Type: </b>{typ}'
                    msg += f'\n\n<a href="{self.__G_DRIVE_BASE_DOWNLOAD_URL.format(file.get("id"))}">Drive Link</a>'
                except TypeError:
                    pass
                if DRIVE_INDEX_URL is not None:
                    url = requests.utils.requote_uri(f'{DRIVE_INDEX_URL}/{file.get("name")}')
                    msg += f' | <a href="{url}">Index Link</a>'
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            LOGGER.error(err)
            return err
        return msg

    def cloneFolder(self, name, local_path, folder_id, parent_id):
        LOGGER.info(f"Syncing: {local_path}")
        files = self.getFilesByFolderId(folder_id)
        new_id = None
        if len(files) == 0:
            return parent_id
        for file in files:
            if file.get('mimeType') == self.__G_DRIVE_DIR_MIME_TYPE:
                self.total_folders += 1
                file_path = os.path.join(local_path, file.get('name'))
                current_dir_id = self.create_directory(file.get('name'), parent_id)
                new_id = self.cloneFolder(file.get('name'), file_path, file.get('id'), current_dir_id)
            else:
                try:
                    self.total_files += 1
                    self.transferred_size += int(file.get('size'))
                except TypeError:
                    pass
                try:
                    self.copyFile(file.get('id'), parent_id)
                    new_id = parent_id
                except Exception as e:
                    if isinstance(e, RetryError):
                        LOGGER.info(f"Total attempts: {e.last_attempt.attempt_number}")
                        err = e.last_attempt.exception()
                    else:
                        err = e
                    LOGGER.error(err)
        return new_id

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(5),
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
            self.__set_permission(file_id)
        LOGGER.info("Created: {}".format(file.get("name")))
        return file_id

    def count(self, link):
        try:
            file_id = self.getIdFromUrl(link)
        except (KeyError, IndexError):
            msg = "Drive ID not found"
            return msg
        msg = ""
        LOGGER.info(f"Counting: {file_id}")
        try:
            meta = self.getFileMetadata(file_id)
            mime_type = meta.get('mimeType')
            if mime_type == self.__G_DRIVE_DIR_MIME_TYPE:
                self.gDrive_directory(meta)
                msg += f'<b>Name: </b><code>{meta.get("name")}</code>'
                msg += f'\n<b>Size: </b>{get_readable_file_size(self.total_bytes)}'
                msg += f'\n<b>Type: </b>Folder'
                msg += f'\n<b>SubFolders: </b>{self.total_folders}'
                msg += f'\n<b>Files: </b>{self.total_files}'
            else:
                msg += f'<b>Name: </b><code>{meta.get("name")}</code>'
                if mime_type is None:
                    mime_type = 'File'
                self.total_files += 1
                self.gDrive_file(meta)
                msg += f'\n<b>Size: </b>{get_readable_file_size(self.total_bytes)}'
                msg += f'\n<b>Type: </b>{mime_type}'
                msg += f'\n<b>Files: </b>{self.total_files}'
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace('>', '').replace('<', '')
            LOGGER.error(err)
            return err
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

    def get_recursive_list(self, file, root_id="root"):
        return_list = []
        if not root_id:
            root_id = file.get('teamDriveId')
        if root_id == "root":
            root_id = self.__service.files().get(fileId='root', fields="id").execute().get('id')
        x = file.get("name")
        y = file.get("id")
        while y != root_id:
            return_list.append(x)
            file = self.__service.files().get(
                fileId=file.get("parents")[0],
                supportsAllDrives=True,
                fields='id, name, parents'
            ).execute()
            x = file.get("name")
            y = file.get("id")
        return_list.reverse()
        return return_list

    def escapes(self, str_val):
        chars = ['\\', "'", '"', r'\a', r'\b', r'\f', r'\n', r'\r', r'\t']
        for char in chars:
            str_val = str_val.replace(char, '\\' + char)
        return str_val

    def drive_query_backup(self, parent_id, file_name):
        file_name = self.escapes(str(file_name))
        query = f"'{parent_id}' in parents and (name contains '{file_name}')"
        response = self.__service.files().list(supportsTeamDrives=True,
                                               includeTeamDriveItems=True,
                                               q=query,
                                               spaces='drive',
                                               pageSize=1000,
                                               fields='files(id, name, mimeType, size, parents)',
                                               orderBy='folder, modifiedTime desc').execute()["files"]
        return response

    def drive_query(self, parent_id, search_type, file_name):
        query = ""
        if search_type is not None:
            if search_type == '-d':
                query += "mimeType = 'application/vnd.google-apps.folder' and "
            elif search_type == '-f':
                query += "mimeType != 'application/vnd.google-apps.folder' and "
        var = re.split('[ ._,\\[\\]-]+', file_name)
        for text in var:
            if text != '':
                query += f"name contains '{text}' and "
        query += "trashed=false"
        response = []
        try:
            if parent_id != "root":
                response = self.__service.files().list(supportsTeamDrives=True,
                                                       includeTeamDriveItems=True,
                                                       teamDriveId=parent_id,
                                                       q=query,
                                                       corpora='drive',
                                                       spaces='drive',
                                                       pageSize=1000,
                                                       fields='files(id, name, mimeType, size, teamDriveId, parents)',
                                                       orderBy='folder, modifiedTime desc').execute()["files"]
            else:
                response = self.__service.files().list(q=query + " and 'me' in owners",
                                                       pageSize=1000,
                                                       spaces='drive',
                                                       fields='files(id, name, mimeType, size, parents)',
                                                       orderBy='folder, modifiedTime desc').execute()["files"]
        except Exception as e:
            LOGGER.exception(f"Failed to call the drive api")
            LOGGER.exception(e)
        if len(response) <= 0:
            response = self.drive_query_backup(parent_id, file_name)
        return response

    def drive_list(self, file_name):
        file_name = self.escapes(file_name)
        search_type = None
        if re.search("^-d ", file_name, re.IGNORECASE):
            search_type = '-d'
            file_name = file_name[2: len(file_name)]
        elif re.search("^-f ", file_name, re.IGNORECASE):
            search_type = '-f'
            file_name = file_name[2: len(file_name)]
        if len(file_name) > 2:
            remove_list = ['A', 'a', 'X', 'x']
            if file_name[1] == ' ' and file_name[0] in remove_list:
                file_name = file_name[2: len(file_name)]
        msg = ''
        index = -1
        content_count = 0
        reached_max_limit = False
        add_title_msg = True
        for parent_id in DRIVE_ID:
            add_drive_title = True
            response = self.drive_query(parent_id, search_type, file_name)
            index += 1
            if response:
                for file in response:
                    if add_title_msg:
                        msg = f'<h4>Query: {file_name}</h4><br>'
                        add_title_msg = False
                    if add_drive_title:
                        msg += f"╾────────────╼<br><b>{DRIVE_NAME[index]}</b><br>╾────────────╼<br>"
                        add_drive_title = False
                    # Detect whether current entity is a folder or file
                    if file.get('mimeType') == "application/vnd.google-apps.folder":
                        msg += f"🗂️<code>{file.get('name')}</code> <b>(folder)</b><br>" \
                               f"<b><a href='https://drive.google.com/drive/folders/{file.get('id')}'>Drive Link</a></b>"
                        if INDEX_URL[index] is not None:
                            url_path = "/".join(
                                [requests.utils.quote(n, safe='') for n in self.get_recursive_list(file, parent_id)])
                            url = f'{INDEX_URL[index]}/{url_path}/'
                            msg += f'<b> | <a href="{url}">Index Link</a></b>'
                    else:
                        msg += f"📄<code>{file.get('name')}</code> <b>({get_readable_file_size(int(file.get('size')))})" \
                               f"</b><br><b><a href='https://drive.google.com/uc?id={file.get('id')}" \
                               f"&export=download'>Drive Link</a></b>"
                        if INDEX_URL[index] is not None:
                            url_path = "/".join(
                                [requests.utils.quote(n, safe='') for n in self.get_recursive_list(file, parent_id)])
                            url = f'{INDEX_URL[index]}/{url_path}'
                            msg += f'<b> | <a href="{url}">Index Link</a></b>'
                    msg += '<br><br>'
                    content_count += 1
                    if content_count >= telegraph_limit:
                        reached_max_limit = True
                        break

        if msg != '':
            self.telegraph_content.append(msg)

        if len(self.telegraph_content) == 0:
            return "Found nothing", None

        for content in self.telegraph_content:
            self.path.append(
                telegra_ph.create_page(title='SearchX',
                                          author_name='XXX',
                                          author_url='https://github.com/l3v11',
                                          html_content=content)['path'])

        msg = "Found " + ("too many" if content_count > telegraph_limit else f"{content_count}") + " results"

        if reached_max_limit:
            msg += "\n<i>(Top " + f"{telegraph_limit}" + " will appear)</i>"

        buttons = button_builder.ButtonMaker()
        buttons.build_button("VIEW HERE", f"https://telegra.ph/{self.path[0]}")

        return msg, InlineKeyboardMarkup(buttons.build_menu(1))
