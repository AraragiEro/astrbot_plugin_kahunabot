from datetime import datetime, timedelta, timezone
from peewee import DoesNotExist
from concurrent.futures import ThreadPoolExecutor
from playhouse.shortcuts import model_to_dict
import asyncio

from .character import Character
from ..evesso_server.eveesi import verify_token, characters_character
from ..evesso_server.eveesi import corporations_corporation_id_roles

# import logger
from ..log_server import logger

#import Exception
from ...utils import KahunaException

class CharacterManager():
    init_status = False
    character_dict: dict = dict()

    @classmethod
    def init(cls):
        cls.init_character_dict()

    @classmethod
    def init_character_dict(cls):
        if not cls.init_status:
            character_list = Character.get_all_characters()
            for character in character_list:
                character_obj = Character(
                    character_id=character.character_id,
                    character_name=character.character_name,
                    QQ=character.QQ,
                    create_date=character.create_date,
                    token=character.token,
                    refresh_token=character.refresh_token,
                    expires_date=character.expires_date,
                    corp_id = character.corp_id,
                )
                cls.character_dict[character.character_id] = character_obj

        logger.info(f"init character dict complete. {id(cls)}")

    @classmethod
    def refresh_all_characters_at_init(cls):
        cls.refresh_all_characters_token()
        cls.refresh_all_character_directer()
        for character_obj in cls.character_dict.values():
            character_obj.insert_to_db()

        cls.init_status = True

    @classmethod
    def refresh_all_characters_token(cls):
        logger.info("refresh all characters token at beginning")
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(character.refresh_character_token) for character in cls.character_dict.values()]
            for future in futures:
                future.result()
        logger.info("refresh all characters complete")

    @classmethod
    def refresh_all_character_directer(cls):
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [(character, executor.submit(cls.is_character_corp_directer, character)) for character in cls.character_dict.values()]
            for character, future in futures:
                character.director = future.result()

    @classmethod
    def get_character_by_id(cls, character_id):
        res = cls.character_dict.get(character_id, None)
        if not res:
            raise KahunaException('Character not found')
        return res

    @classmethod
    def get_character_by_name_qq(cls, character_name: str, qq: int) -> Character:
        for character in cls.character_dict.values():
            if character.character_name == character_name and character.QQ == qq:
                return character
                break
        raise KahunaException('无法使用qq和角色名匹配角色对象。请先进行授权。')

    @classmethod
    def is_character_corp_directer(cls, character):
        role_info = corporations_corporation_id_roles(character.ac_token, character.corp_id)
        if not role_info:
            return False

        for corp_member in role_info:
            if corp_member['character_id'] == character.character_id:
                if 'Director' in corp_member['roles']:
                    return True
                else:
                    return False
        return False

    @classmethod
    def create_new_character(cls, token_data, user_qq):
        character_verify_data = verify_token(token_data[0])
        if not character_verify_data:
            logger.error('No character info found')

        character_id = character_verify_data['CharacterID']
        character_data = characters_character(character_id)
        corp_id = character_data['corporation_id']
        character_name = character_verify_data['CharacterName']
        expires_time = datetime.fromisoformat(character_verify_data["ExpiresOn"] + "Z")
        expires_time = expires_time.astimezone(timezone(timedelta(hours=+8), 'Shanghai'))
        # try:
        #     character = M_Character.get(M_Character.character_id == character_id)
        # except DoesNotExist:
        #     character = M_Character()

        if character_id not in cls.character_dict:
            character = Character(
                character_id = character_id,
                character_name = character_name,
                QQ = user_qq,
                create_date = datetime.now(),
                token = token_data[0],
                refresh_token = token_data[1],
                expires_date = expires_time,
                corp_id = corp_id
            )
        else:
            character = cls.character_dict[character_id]
            character.character_id = character_id
            character.character_name = character_name
            character.QQ = user_qq
            character.create_date = datetime.now()
            character.token = token_data[0]
            character.refresh_token = token_data[1]
            character.expires_date = expires_time
            character.corp_id = corp_id
        character.director = cls.is_character_corp_directer(character)

        character.insert_to_db()
        cls.character_dict[character_id] = character

        return model_to_dict(character.get_from_db())

    @classmethod
    def get_user_all_characters(cls, user_id):
        return [character for character in cls.character_dict.values() if character.QQ == user_id]