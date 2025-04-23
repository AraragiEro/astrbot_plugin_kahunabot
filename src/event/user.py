from datetime import datetime

# import logger
from astrbot.api import logger

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

# kahuna model
from .utils import kahuna_debug_info
from ..service.user_server.user_manager import UserManager
from ..service.evesso_server.eveesi import characters_character
from ..service.feishu_server.feishu_kahuna import FeiShuKahuna

# import Exception
from ..utils import (
    KahunaException,
    get_user_tmp_cache_prefix,
    get_beijing_utctime,
    get_debug_qq
)


def get_user(event: AstrMessageEvent):
    if get_debug_qq():
        user_qq = get_debug_qq()
    else:
        user_qq = int(event.get_sender_id())

    return user_qq

class UserEvent():
    @staticmethod
    def create(event: AstrMessageEvent, user_qq: int):
        return event.plain_result(UserManager.create_user(user_qq).info)

    @staticmethod
    def addMemberTime(event: AstrMessageEvent, user_qq: int, time_day: int):
        expire_date = UserManager.add_member_time(user_qq, time_day)
        return event.plain_result(f"用户: {user_qq} 已添加 {time_day} 天。\n"
                                  f"当前剩余时间：{expire_date - datetime.now()}")

    @staticmethod
    def deleteUser(event: AstrMessageEvent, user_qq: int):
        UserManager.delete_user(user_qq)
        return event.plain_result("执行完成。")

    @staticmethod
    def clearMemberTime(event: AstrMessageEvent, user_qq: int):
        UserManager.clean_member_time(user_qq)
        return event.plain_result(f"用户 {user_qq} 时间已清零")

    @staticmethod
    def self_info(event: AstrMessageEvent):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        return event.plain_result(user.info)

    @staticmethod
    def setMainCharacter(event: AstrMessageEvent):
        user_qq = get_user(event)
        main_character= " ".join(event.get_message_str().split(" ")[2:])
        UserManager.set_main_character(user_qq, main_character)
        return event.plain_result("设置主角色 执行完成")

    @staticmethod
    def sign(event: AstrMessageEvent):
        user_qq = get_user(event)
        if UserManager.user_exists(user_qq):
            return event.plain_result(f'用户已存在。')
        user_obj = UserManager.create_user(user_qq)
        return event.plain_result(user_obj.info)

    @staticmethod
    def addalias(event: AstrMessageEvent):
        user_qq = get_user(event)
        context = " ".join(event.get_message_str().split(" ")[2:])

        user = UserManager.get_user(user_qq)
        character_list = context.split(",")
        character_id_list = []
        insert_fail_list = []
        for character in character_list:
            character_info = characters_character(character)
            if character_info:
                character_id_list.append([character, character_info["name"]])
            else:
                insert_fail_list.append(character)
        user.add_alias_character(character_id_list)
        res = f"执行完成。以下id未获得角色信息添加失败。"
        if insert_fail_list:
            res += f"\n{insert_fail_list}"
        return event.plain_result(res)

    @staticmethod
    def sheet_create(event: AstrMessageEvent):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        spreadsheet = FeiShuKahuna.create_user_plan_spreadsheet(user.user_qq)
        FeiShuKahuna.create_default_spreadsheet(spreadsheet)
        return event.plain_result(f'表格已创建，url: {spreadsheet.url}')

    @staticmethod
    def sheet_url(event: AstrMessageEvent, plan_name: str):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        spreadsheet = FeiShuKahuna.get_user_plan_spreadsheet(user.user_qq, plan_name)

        return event.plain_result(f'您的数据报表： {spreadsheet.url}')
