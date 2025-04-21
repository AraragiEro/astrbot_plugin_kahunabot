from functools import lru_cache
from tokenize import group
from peewee import DoesNotExist

from ..sde_service import SdeUtils
from ..sde_service.database import IndustryActivityMaterials, IndustryActivityProducts, IndustryBlueprints

class BPManager:
    @classmethod
    @lru_cache(maxsize=1000)
    def get_bp_materials(cls, type_id: int) -> dict:
        material_search = (
            IndustryActivityMaterials
                .select(IndustryActivityMaterials.materialTypeID, IndustryActivityMaterials.quantity)
                .join(IndustryActivityProducts,
                      on=(IndustryActivityMaterials.blueprintTypeID==IndustryActivityProducts.blueprintTypeID))
                .where((IndustryActivityProducts.productTypeID==type_id) &
                       (IndustryActivityProducts.blueprintTypeID != 45732) &
                       ((IndustryActivityMaterials.activityID == 1) | (IndustryActivityMaterials.activityID == 11)))
        )
        return {material.materialTypeID: material.quantity for material in material_search}

    @classmethod
    @lru_cache(maxsize=1000)
    def get_bp_product_quantity_typeid(cls, type_id: int) -> int:
        try:
            #45732是一个测试用数据，会导致误判，需要特殊处理
            product_quantity = IndustryActivityProducts.select(IndustryActivityProducts.quantity).where(
                (IndustryActivityProducts.productTypeID == type_id) &
                (IndustryActivityProducts.blueprintTypeID != 45732)
            ).get().quantity
        except DoesNotExist:
            product_quantity = 1  # 或者你想要的默认值

        return product_quantity

    # @classmethod
    # def get_formula_id_by_prod_typeid(cls, type_id: int, unrefined: bool = False) -> int:
    #     ressults = (IndustryActivityProducts
    #              .select(IndustryActivityProducts.blueprintTypeID, IndustryActivityProducts.quantity)
    #              .where(IndustryActivityProducts.productTypeID == type_id))
    #
    #     for res in ressults:
    #         if unrefined and res.quantity == 1:
    #             return res.blueprintTypeID
    #         elif not unrefined and res.quantity > 1:
    #             return res.blueprintTypeID
    #
    # @classmethod
    # def get_manubp_id_by_prod_typeid(cls, type_id: int) -> int:
    #     return (IndustryActivityProducts
    #              .select(IndustryActivityProducts.blueprintTypeID)
    #              .where(IndustryActivityProducts.productTypeID == type_id)).scalar()

    @classmethod
    @lru_cache(maxsize=100)
    def get_bp_id_by_prod_typeid(cls, type_id: int) -> int:
        return (
            IndustryActivityProducts
                 .select(IndustryActivityProducts.blueprintTypeID)
                 .where((IndustryActivityProducts.productTypeID == type_id) &
                        (IndustryActivityProducts.blueprintTypeID != 45732)).scalar()
        )

    @classmethod
    @lru_cache(maxsize=100)
    def get_bp_id_by_pbpname(cls, bp_name) -> int:
        bp_maybe_type_id = SdeUtils.get_id_by_name(bp_name)
        if not bp_maybe_type_id:
            return None
        bp_id = (IndustryActivityProducts
                 .select(IndustryActivityProducts.blueprintTypeID)
                 .where(IndustryActivityProducts.blueprintTypeID == bp_maybe_type_id)
                 .scalar())
        if bp_id:
            return bp_id
        return None

    @classmethod
    @lru_cache(maxsize=1000)
    def check_product_id_existence(cls, product_type_id: int) -> bool:
        return IndustryActivityProducts.select().where(IndustryActivityProducts.productTypeID == product_type_id).exists()

    @classmethod
    @lru_cache(maxsize=1000)
    def get_production_time(cls, product_id: int) -> int:
        """
        获取指定产品的制造活动时间（秒）
        参数：
            product_id (int): 产品ID
        返回：
            int: 制造活动时间，单位秒。如果未找到返回0
        """
        details = cls.get_blueprint_details(product_id)
        if details is None:
            return 0
            
        for activity in details['activities']:
            if activity['activityID'] == 1 or activity['activityID'] == 11:  # 制造活动
                return activity['time']
        return 0

    @classmethod
    @lru_cache(maxsize=1000)
    def get_action_id(cls, product_id: int) -> int:
        """
        获取指定产品的制造活动时间（秒）
        参数：
            product_id (int): 产品ID
        返回：
            int: 制造活动时间，单位秒。如果未找到返回0
        """
        details = cls.get_blueprint_details(product_id)
        if details is None:
            return 0

        for activity in details['activities']:
            if activity['activityID'] == 1 or activity['activityID'] == 11:  # 制造活动
                return activity['activityID']
        return 0

    @classmethod
    @lru_cache(maxsize=1000)
    def get_chunk_runs(cls, product_id: int) -> int:
        """
        计算单个蓝图每日可完成的制造流程数
        参数：
            product_id (int): 产品ID
        返回：
            int: 每日可完成的制造流程数
        """
        production_time = cls.get_production_time(product_id)
        if production_time <= 0:
            return 0
        return max(1, 86400 // production_time)  # 86400秒 = 1天

    @classmethod
    @lru_cache(maxsize=1000)
    def get_blueprint_details(cls, product_id: int) -> dict:
        """
        根据产品ID返回蓝图的详细信息字典。
        参数：
            product_id (int): 产品的ID
        返回：
            dict: 包含蓝图详细信息的字典，包括基本属性、材料和活动时间
        """
        from ..sde_service.database import InvTypes, IndustryActivityMaterials, IndustryActivities
        
        blueprint_details = {
            'product_info': {},
            'materials': [],
            'activities': []
        }
        
        try:
            # 获取产品基本信息
            product = InvTypes.get(InvTypes.typeID == product_id)
            blueprint_details['product_info'] = {
                'typeID': product.typeID,
                'typeName': product.typeName,
                'description': product.description,
                'mass': product.mass,
                'volume': product.volume,
                'basePrice': product.basePrice
            }
            
            # 获取所有与该产品相关的蓝图活动材料
            materials = IndustryActivityMaterials.select(
                    IndustryActivityMaterials.materialTypeID,
                    IndustryActivityMaterials.quantity  # 
                ).join(
                IndustryActivityProducts,
                on=(IndustryActivityMaterials.blueprintTypeID == 
                    IndustryActivityProducts.blueprintTypeID)
            ).where((IndustryActivityProducts.productTypeID == product_id) &
                    (IndustryActivityProducts.blueprintTypeID != 45732) &
                    ((IndustryActivityMaterials.activityID == 1) | (IndustryActivityMaterials.activityID == 11)))
            
            for material in materials:
                blueprint_details['materials'].append({
                    'material_typeID': material.materialTypeID,
                    'quantity': material.quantity
                })
            
            # 获取所有与该产品相关的蓝图活动信息
            # 首先通过 IndustryActivityProducts 获取 blueprintTypeID
            blueprint_type_id = IndustryActivityProducts.select(
                IndustryActivityProducts.blueprintTypeID
            ).where(
                (IndustryActivityProducts.productTypeID == product_id) &
                (IndustryActivityProducts.blueprintTypeID != 45732)
            ).get().blueprintTypeID
            
            # 然后使用 blueprintTypeID 查询 IndustryActivities
            activities = IndustryActivities.select(
                IndustryActivities.activityID,
                IndustryActivities.time
            ).where(
                (IndustryActivities.blueprintTypeID == blueprint_type_id) &
                (IndustryActivityProducts.blueprintTypeID != 45732)
            )
            
            for activity in activities:
                blueprint_details['activities'].append({
                    'activityID': activity.activityID,
                    'time': activity.time
                })

        except DoesNotExist as e:
            return None
        
        return blueprint_details

    @classmethod
    def get_typeid_by_bpid(cls, blueprint_id: int):
        return (IndustryActivityProducts.select(IndustryActivityProducts.productTypeID)
                                  .where(IndustryActivityProducts.blueprintTypeID == blueprint_id).scalar())

    @classmethod
    @lru_cache(maxsize=1000)
    def get_productionmax_by_bpid(cls, blueprint_id: int):
        product_id = cls.get_typeid_by_bpid(blueprint_id)
        meta = SdeUtils.get_metaname_by_typeid(product_id)
        cate = SdeUtils.get_category_by_id(product_id)
        if meta == 'Faction' and cate == 'Ship':
            return 1
        return (IndustryBlueprints.select(IndustryBlueprints.maxProductionLimit)
                                  .where(IndustryBlueprints.blueprintTypeID == blueprint_id).scalar())