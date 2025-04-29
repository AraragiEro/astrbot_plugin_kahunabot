import json

# from ..database_server.model import Matcher as M_Matcher
from ..database_server.sqlalchemy.kahuna_database_utils import (
    # Matcher,
    MatcherDBUtils
)

MATCHER_KEY = ["bp", "market_group", "group", "meta", "category"]

class Matcher:
    matcher_name = ""
    user_qq = 0
    matcher_type = ""
    matcher_data = {matcher_k: dict() for matcher_k in MATCHER_KEY}

    def __init__(self, matcher_name, user_qq, matcher_type):
        self.matcher_name = matcher_name
        self.user_qq = user_qq
        self.matcher_type = matcher_type
        self.matcher_data = {matcher_k: dict() for matcher_k in MATCHER_KEY}

    @classmethod
    def init_from_db_data(cls, data):
        matcher = Matcher(data.matcher_name, data.user_qq, data.matcher_type)
        matcher.matcher_data = json.loads(data.matcher_data)

        return matcher

    async def get_from_db(self):
        return await MatcherDBUtils.select_matcher_by_name(self.matcher_name)


    async def insert_to_db(self):
        obj = await self.get_from_db()
        if not obj:
            obj = MatcherDBUtils.get_obj()

        obj.matcher_name = self.matcher_name
        obj.user_qq = self.user_qq
        obj.matcher_type = self.matcher_type
        obj.matcher_data = json.dumps(self.matcher_data)

        await MatcherDBUtils.save_obj(obj)

    async def delete_from_db(self):
        await MatcherDBUtils.delete_matcher_by_name(self.matcher_name)
