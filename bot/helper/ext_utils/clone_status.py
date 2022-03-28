from bot.helper.ext_utils.bot_utils import get_readable_file_size

class CloneStatus:
    def __init__(self, size=0):
        self.size = size
        self.name = ''
        self.status = False
        self.source_folder_name = ''
        self.source_folder_link = ''

    def set_status(self, stat):
        self.status = stat

    def set_name(self, name=''):
        self.name = name

    def get_name(self):
        return self.name

    def add_size(self, value):
        self.size += int(value)

    def get_size(self):
        return get_readable_file_size(int(self.size))

    def done(self):
        return self.status

    def set_source_folder(self, folder_name, link):
        self.source_folder_name = folder_name
        self.source_folder_link = link
