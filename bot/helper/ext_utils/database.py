from pymongo import MongoClient
from pymongo.errors import PyMongoError

from bot import LOGGER, AUTHORIZED_USERS, BOOKMARKS, DATABASE_URL

class DatabaseHelper:

    def __init__(self):
        self.__err = False
        self.__client = None
        self.__db = None
        self.__connect()

    def __connect(self):
        try:
            self.__client = MongoClient(DATABASE_URL)
            self.__db = self.__client['SearchX']
        except PyMongoError as err:
            LOGGER.error(err)
            self.__err = True

    def load_db(self):
        if self.__err:
            return
        if self.__db.users.find_one():
            users_dict = self.__db.users.find().sort("user_id")
            for user in users_dict:
                AUTHORIZED_USERS.add(user["user_id"])
        if self.__db.bms.find_one():
            bms_dict = self.__db.bms.find().sort("drive_key")
            for bm in bms_dict:
                BOOKMARKS[bm["drive_key"]] = str(bm["drive_id"])
        self.__client.close()

    def auth_user(self, user_id):
        if self.__err:
            return
        self.__db.users.insert_one({"user_id": user_id})
        self.__client.close()
        return 'Authorization granted'

    def unauth_user(self, user_id):
        if self.__err:
            return
        self.__db.users.delete_one({"user_id": user_id})
        self.__client.close()
        return 'Authorization revoked'

    def add_bm(self, drive_key, drive_id):
        if self.__err:
            return
        self.__db.bms.insert_one({"drive_key": drive_key, "drive_id": drive_id})
        self.__client.close()
        return 'Bookmark added'

    def remove_bm(self, drive_key):
        if self.__err:
            return
        self.__db.bms.delete_one({"drive_key": drive_key})
        self.__client.close()
        return 'Bookmark removed'

if DATABASE_URL is not None:
    DatabaseHelper().load_db()
