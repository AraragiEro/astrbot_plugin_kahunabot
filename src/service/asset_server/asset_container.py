from enum import Enum
from cachetools import cached, TTLCache

# Kahuna model
from ..sde_service.utils import SdeUtils
from ..database_server.model import AssetCache
from ..database_server.model import AssetContainer as M_AssetContainer
from ..character_server.character_manager import CharacterManager
from ..industry_server.structure import StructureManager

class ContainerTag(Enum):
    bp = 'blueprint'
    reac = 'reaction'
    manu = 'manufacturing'
    sell = 'sell'

class AssetContainer:
    asset_location_id = 0
    asset_location_type = 0
    asset_name = 0
    asset_owner_qq = 0
    structure_id = 0
    solar_system_id = 0
    asset_owner_id = 0
    asset_owner_type = 0
    tag = None

    def __init__(self, asset_location_id: int, asset_location_type: str, asset_name: str, asset_owner_qq: int):
        self.asset_location_id = asset_location_id
        self.asset_location_type = asset_location_type
        self.asset_name = asset_name
        self.asset_owner_qq = asset_owner_qq

    @classmethod
    def get_all_asset_container(cls):
        return M_AssetContainer.select()

    @classmethod
    def operater_has_container_permission(cls, operate_qq: int, owner_id: int):
        operate_qq_list = CharacterManager.get_user_all_characters(operate_qq)
        for character in operate_qq_list:
            if (owner_id == character.character_id and operate_qq == character.QQ) or \
               (owner_id == character.corp_id and operate_qq == character.QQ):
                return True
        return False

    @classmethod
    def find_secret_data(cls, secret_type: str) -> list:
        item_id = SdeUtils.get_id_by_name(secret_type)
        if not item_id:
            return []

        result = AssetCache.select().where(
            (AssetCache.type_id == item_id))
        find_list = [data for data in result]
        return find_list

    @classmethod
    def find_container(cls, secret_type: str, user_qq: int, character):
        # 1. 获取数据
        # 在asset_cache找到type_id==get_id_by_name(secret_type) and quantity==secret_quantity的条目
        secret_data_list = cls.find_secret_data(secret_type)

        count_dict = {}
        for data in secret_data_list:
            if (data.location_id, data.location_flag, data.owner_id) not in count_dict:
                count_dict[(data.location_id, data.location_flag, data.owner_id)] = 0
            count_dict[(data.location_id, data.location_flag, data.owner_id)] += data.quantity
        count_list = [(*key, value) for key, value in count_dict.items()]

        verified_container = []
        # 2. 权限校验
        for data in count_list:
            if cls.operater_has_container_permission(user_qq, data[2]):
                verified_container.append(data)

        container_data = []
        for data in verified_container:
            # 找到secret物品所在建筑
            structure_id, structure_flag = SdeUtils.get_structure_id_from_location_id(data[0], data[1])

            if structure_id and structure_flag:
                container_data.append((data[0], data[1], structure_id, data[3]))

        container_info = []
        for data in container_data:
            structure = StructureManager.get_structure(data[2], ac_token=character.ac_token)
            if not structure:
                continue
            info = dict(structure)
            info.update({
                'location_id': data[0],
                'location_flag': data[1],
                'structure_type': SdeUtils.get_name_by_id(info['type_id']),
                'exist_quantity': data[3],

            })
            if info:
                container_info.append(info)

        return container_info

    def get_from_db(self):
        return M_AssetContainer.get_or_none(
            (M_AssetContainer.asset_location_id == self.asset_location_id) &
            (M_AssetContainer.asset_owner_qq == self.asset_owner_qq))

    def insert_to_db(self):
        obj = self.get_from_db()
        if not obj:
            obj = M_AssetContainer()

        """
        asset_location_id = IntegerField()
        asset_location_type = CharField()
        solar_system_id = IntegerField()
        asset_name = TextField()
        asset_owner_id = IntegerField()
        asset_owner_type = CharField()
        asset_owner_qq = IntegerField()
        """
        obj.asset_location_id = self.asset_location_id
        obj.asset_location_type = self.asset_location_type
        obj.structure_id = self.structure_id
        obj.solar_system_id = self.solar_system_id
        obj.asset_name = self.asset_name
        obj.asset_owner_id = self.asset_owner_id
        obj.asset_owner_type = self.asset_owner_type
        obj.asset_owner_qq = self.asset_owner_qq
        obj.tag = self.tag

        obj.save()

    @classmethod
    def get_contain_id_by_qq_tag(cls, qq: int, tag: str) -> list[int]:
        return [container.asset_location_id for container in
                M_AssetContainer.select().where(M_AssetContainer.asset_owner_qq == qq, M_AssetContainer.tag == tag)]

    def __str__(self):
        return (f"id: {self.asset_location_id}\n"
                f"name: {self.asset_name}\n"
                f"所属用户: {self.asset_owner_qq}\n"
                f"tag: {self.tag}\n")
