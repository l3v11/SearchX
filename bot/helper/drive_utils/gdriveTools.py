import logging
import os
import json
import re
import requests

from telegram import InlineKeyboardMarkup

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from bot import LOGGER, DRIVE_NAME, DRIVE_ID, INDEX_URL, telegra_ph
from bot.helper.telegram_helper import button_builder

logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
telegraph_limit = 95

class GoogleDriveHelper:
    def __init__(self, name=None, listener=None):
        self.listener = listener
        self.name = name
        self.__G_DRIVE_TOKEN_FILE = "token.json"
        # Check https://developers.google.com/drive/scopes for all available scopes
        self.__OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']
        self.__service = self.authorize()
        self.telegraph_content = []
        self.path = []

    def get_readable_file_size(self, size_in_bytes) -> str:
        if size_in_bytes is None:
            return '0B'
        index = 0
        size_in_bytes = int(size_in_bytes)
        while size_in_bytes >= 1024:
            size_in_bytes /= 1024
            index += 1
        try:
            return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'
        except IndexError:
            return 'File too large'

    def authorize(self):
        # Get credentials
        credentials = None
        if os.path.exists(self.__G_DRIVE_TOKEN_FILE):
            credentials = Credentials.from_authorized_user_file(self.__G_DRIVE_TOKEN_FILE, self.__OAUTH_SCOPE)
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())

        return build('drive', 'v3', credentials=credentials, cache_discovery=False)

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
                               f"<b><a href='https://drive.google.com/drive/folders/{file.get('id')}'>Drive</a></b>"
                        if INDEX_URL[index] is not None:
                            url_path = "/".join(
                                [requests.utils.quote(n, safe='') for n in self.get_recursive_list(file, parent_id)])
                            url = f'{INDEX_URL[index]}/{url_path}/'
                            msg += f'<b> | <a href="{url}">DDL</a></b>'
                    else:
                        msg += f"📄<code>{file.get('name')}</code> <b>({self.get_readable_file_size(file.get('size'))})" \
                               f"</b><br><b><a href='https://drive.google.com/uc?id={file.get('id')}" \
                               f"&export=download'>Drive</a></b>"
                        if INDEX_URL[index] is not None:
                            url_path = "/".join(
                                [requests.utils.quote(n, safe='') for n in self.get_recursive_list(file, parent_id)])
                            url = f'{INDEX_URL[index]}/{url_path}'
                            msg += f'<b> | <a href="{url}">DDL</a></b>'
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
