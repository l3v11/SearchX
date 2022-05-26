from redis import Redis

from bot import AUTHORIZED_CHATS, DATABASE_URL, MY_BOOKMARKS, LOGGER

class DatabaseHelper:
    def __init__(self):
        self.redisDB = Redis.from_url(DATABASE_URL)

    def auth_user(self, user_id: int):
        self.redisDB.set(f"auth_{user_id}", '1')
        return 'Authorization granted'

    def unauth_user(self, user_id: int):
        self.redisDB.delete(f"auth_{user_id}")
        return 'Authorization revoked'

    def get_users(self):
        return [int(key.decode('utf-8').split("auth_")[1]) for key in self.redisDB.keys('auth_*')]

    def load_users(self):
        users = self.get_users()
        for user in users:
            AUTHORIZED_CHATS.add(user)

    def add_bm(self, name: str, id: str):
        self.redisDB.set(f"bm_{name}", id)

    def rm_bm(self, name: str):
        self.redisDB.delete(f"bm_{name}")

    def get_bms(self):
        bm_dict = {}
        keys = self.redisDB.keys('bm_*')
        vals = self.redisDB.mget(keys)
        for key, value in zip(keys, vals):
            bm_dict[key.decode('utf-8').split("bm_")[1]] = value.decode('utf-8')
        return bm_dict
    
    def load_bms(self):
        global MY_BOOKMARKS
        MY_BOOKMARKS.update(self.get_bms())

if DATABASE_URL is not None:
    db = DatabaseHelper()
    db.load_users()
    db.load_bms()
    LOGGER.info(f'Database loaded : {str(MY_BOOKMARKS)}')