from tqdm import tqdm

# kahuna model
from ..database_server.model import (Asset as M_Asset,
                                     AssetCache as M_AssetCache,
                                     AssetOwner as M_AssetOwner,
                                     BlueprintAsset as M_BlueprintAsset,
                                     BlueprintAssetCache as M_BlueprintAssetCache)
from ..database_server.connect import DatabaseConectManager
from ..evesso_server.eveesi import (characters_character_assets,
                                    corporations_corporation_assets,
                                    characters_character_id_blueprints,
                                    corporations_corporation_id_blueprints)
from ..evesso_server.eveutils import find_max_page, get_multipages_result
from ..character_server.character import Character

# kahuna logger
from ..log_server import logger

# kahuna KahunaException

# 查价缓存

REGION_FORGE_ID = 10000002
JITA_TRADE_HUB_STRUCTURE_ID = 60003760
FRT_4H_STRUCTURE_ID = 1035466617946


class AssetOwner():
    owner_qq = 0
    owner_type: str = "character"
    owner_id: int = 0
    access_character: Character = None

    def __init__(self, owner_qq: int, owner_type: str, owner_id: int, access_character: Character):
        if owner_type != "character" and owner_type != "corp":
            raise ValueError("Invalid owner_type. [character or corp]")
        self.owner_qq = owner_qq
        self.owner_type = owner_type
        self.owner_id = owner_id
        self.access_character = access_character

    @staticmethod
    def get_all_asset_owner():
        return M_AssetOwner.select()

    def get_from_db(self):
        return M_AssetOwner.get_or_none(
            (M_AssetOwner.asset_owner_id == self.owner_id) &
            (M_AssetOwner.asset_type == self.owner_type))

    @property
    def token_accessable(self):
        if self.owner_type == "character":
            res = characters_character_assets(1, self.access_character.ac_token, self.owner_id)
        elif self.owner_type == "corp":
            res = corporations_corporation_assets(1, self.access_character.ac_token, self.owner_id)
        if not res:
            return False
        return True

    def insert_to_db(self):
        obj = self.get_from_db()
        if not obj:
            obj = M_AssetOwner()

        obj.asset_owner_id = self.owner_id
        obj.asset_type = self.owner_type
        obj.asset_owner_qq = self.owner_qq
        obj.asset_access_character_id = self.access_character.character_id

        obj.save()

    def delete_asset(self):
        M_Asset.delete().where(M_Asset.owner_id == self.owner_id &
                               M_Asset.asset_type == self.owner_type).execute()

    def get_asset(self):
        logger.info(f"开始刷新 {self.owner_type} {self.access_character.character_name} 资产")
        if self.owner_type == "character":
            self.get_owner_asset(characters_character_assets, self.owner_id)
            self.get_owner_bp_asset(characters_character_id_blueprints, self.owner_id)
        elif self.owner_type == "corp":
            self.get_owner_asset(corporations_corporation_assets, self.owner_id)
            self.get_owner_bp_asset(corporations_corporation_id_blueprints, self.owner_id)

    def get_owner_asset(self, asset_esi, owner_id):
        if not self.access_character:
            return
        ac_token = self.access_character.ac_token
        if self.owner_type == "character":
            begin_page = 10
            interval = 20
        else:
            begin_page = 20
            interval = 40
        max_page = find_max_page(asset_esi, ac_token, owner_id, begin_page=begin_page, interval=interval)
        if max_page == 0:
            logger.warning(
                f"find max page = 0 when use {asset_esi.__name__} "
                f"with {self.access_character.character_name} as type {self.owner_type}"
            )
            return

        logger.info("请求资产。")
        results = get_multipages_result(asset_esi, max_page, ac_token, owner_id)
        db = DatabaseConectManager.cache_db()
        with db.atomic():
            M_Asset.delete().where((M_Asset.asset_type == self.owner_type) & (M_Asset.owner_id == self.owner_id)).execute()
            with tqdm(total=len(results), desc="写入数据库", unit="page", ascii='=-') as pbar:
                for result in results:
                    # result = [order for order in result if order["location_id"] == JITA_TRADE_HUB_STRUCTURE_ID]
                    for asset in result:
                        asset.update({"asset_type": self.owner_type, "owner_id": self.owner_id})
                        if "is_blueprint_copy" not in asset:
                            asset["is_blueprint_copy"] = False
                    M_Asset.insert_many(result).execute()
                    pbar.update()

    def get_owner_bp_asset(self, asset_esi, owner_id):
        if not self.access_character:
            return
        ac_token = self.access_character.ac_token
        max_page = find_max_page(asset_esi, ac_token, owner_id, begin_page=1, interval=5)

        logger.info("请求bp资产。")
        results = get_multipages_result(asset_esi, max_page, ac_token, owner_id)
        db = DatabaseConectManager.cache_db()
        with db.atomic():
            M_BlueprintAsset.delete().where((M_BlueprintAsset.owner_type == self.owner_type) &
                                            (M_BlueprintAsset.owner_id == self.owner_id)).execute()
            with tqdm(total=len(results), desc="写入数据库", unit="page", ascii='=-') as pbar:
                for result in results:
                    # result = [order for order in result if order["location_id"] == JITA_TRADE_HUB_STRUCTURE_ID]
                    for asset in result:
                        asset.update({"owner_type": self.owner_type, "owner_id": self.owner_id})
                    M_BlueprintAsset.insert_many(result).execute()
                    pbar.update()

    @property
    def asset_item_count(self):
        count = M_AssetCache.select().where(M_AssetCache.owner_id == self.owner_id).count()
        return count

    def asset_valuation(self):
        pass

