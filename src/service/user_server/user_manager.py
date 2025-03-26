from datetime import datetime
from cachetools import TTLCache
import asyncio
from asyncio import Lock
import threading
import json


from .user import User
from ..database_server.model import User as M_User
from ..character_server.character_manager import CharacterManager
from ..log_server import logger

# import Exception
from ...utils import KahunaException

ESI_CACHE = TTLCache(maxsize=100, ttl=300)


class UserManager():
    init_status = False
    lock = Lock()
    user_dict = dict() # {qq_id: User()}

    @classmethod
    def init(cls):
        cls.init_user_dict()

    @classmethod
    def init_user_dict(cls):
        if not cls.init_status:
            user_list = M_User.select()
            for user in user_list:
                usr_obj = User(
                    qq=user.user_qq,
                    create_date=user.create_date,
                    expire_date=user.expire_date
                )
                if user.main_character_id:
                    usr_obj.main_character_id = user.main_character_id
                cls.user_dict[usr_obj.user_qq] = usr_obj
        cls.init_status = True
        logger.info(f"init user list complete. {id(cls)}")

    @classmethod
    def get_main_character_id(cls, qq: int):
        user = cls.user_dict.get(qq, None)
        if not user:
            raise KahunaException("用户主角色不存在，请先注册和设置主角色。")
        return user.main_character_id

    @classmethod
    def set_main_character(cls, qq: int, main_character: str):
        user = cls.get_user(qq)
        main_character = CharacterManager.get_character_by_name_qq(main_character, qq)
        user.main_character_id = main_character.character_id

        user.insert_to_db()

    @classmethod
    def create_user(cls, qq: int) -> User:
        if (user := cls.user_dict.get(qq, None)) is None:
            user = User(qq=qq, create_date=datetime.now(), expire_date=datetime.now())
        user.init_time()
        user.insert_to_db()
        cls.user_dict[user.user_qq] = user

        return user

    @classmethod
    def user_exists(cls, qq: int) -> bool:
        return qq in cls.user_dict.keys()

    @classmethod
    def get_user(cls, qq: int) -> User:
        if (user := cls.user_dict.get(qq, None)) is None:
            raise KahunaException("用户不存在。")
        return user

    @classmethod
    def add_member_time(cls, qq: int, days: int):
        if (user := cls.user_dict.get(qq, None)) is None:
            raise KahunaException("用户不存在。")
        return user.add_member_time(days)

    @classmethod
    def delete_user(cls, qq: int):
        if (user := cls.user_dict.get(qq, None)) is None:
            return
        user.delete()
        cls.user_dict.pop(qq)

    @classmethod
    def clean_member_time(cls, qq: int) -> User:
        if (user := cls.user_dict.get(qq, None)) is None:
            raise KahunaException("用户不存在。")
        user.clean_member_time()

        return user
