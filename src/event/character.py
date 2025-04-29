import json

# import logger
from astrbot.api import logger

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register

# # kahuna model
from ..service.character_server.character_manager import CharacterManager
from ..service.evesso_server.oauth import get_auth_url, get_token

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


class CharacterEvent():
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @staticmethod
    def auth(event: AstrMessageEvent):
        get_user(event)

        return event.plain_result(f'{get_auth_url()}\n 请点击链接认证后，等待浏览器变为空白后，将链接使用.角色 添加 [链接] 指令私聊给机器人。')

    @staticmethod
    async def add(event: AstrMessageEvent, back_url):
        user_qq = get_user(event)
        at, rt, et = get_token(back_url)
        character_info = await CharacterManager.create_new_character([at, rt, et], user_qq)
        print_info = (f"绑定成功，信息已写入。\n"
                      f"角色名：{character_info['character_name']}\n"
                      f"QQ: {character_info['QQ']}\n"
                      f"创建时间：{character_info['create_date']}\n")
        logger.info(4)
        return event.plain_result(print_info)