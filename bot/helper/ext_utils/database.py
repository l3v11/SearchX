from pymongo import MongoClient

from bot import AUTHORIZED_CHATS, DATABASE_URL

class DatabaseHelper:
    def __init__(self):
        self.mongodb = MongoClient(host=DATABASE_URL)["SearchX"]
        self.col = self.mongodb["users"]

    def auth_user(self, user_id: int):
        self.col.insert_one({"user_id": user_id})
        return 'Authorization granted'

    def unauth_user(self, user_id: int):
        self.col.delete_many({"user_id": user_id})
        return 'Authorization revoked'

    def get_users(self):
        return self.col.find().sort("user_id")

    def load_users(self):
        users = self.get_users()
        for user in users:
            AUTHORIZED_CHATS.add(user['user_id'])

if DATABASE_URL is not None:
    DatabaseHelper().load_users()
