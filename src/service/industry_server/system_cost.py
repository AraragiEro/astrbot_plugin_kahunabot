from cachetools import TTLCache, cached

from ..database_server.sqlalchemy.kahuna_database_utils import (
    SystemCostCacheDBUtils, SystemCostDBUtils
)
from ..evesso_server import eveesi
from ...utils import chunks

class SystemCost:
    @classmethod
    async def refresh_system_cost(cls):
        result = await eveesi.industry_systems(log=True)

        insert_data = []
        for item in result:
            data = {"solar_system_id": item["solar_system_id"]}
            for cost in item["cost_indices"]:
                data[cost["activity"]] = cost["cost_index"]
            insert_data.append(data)

        await SystemCostDBUtils.delete_all()
        for chunk in chunks(insert_data, 1000):
            await SystemCostDBUtils.insert_many(chunk)

        await cls.copy_to_cache()

    @classmethod
    async def copy_to_cache(cls):
        await SystemCostCacheDBUtils.copy_base_to_cache()

    system_cos_cache = TTLCache(maxsize=1000, ttl=20 * 60)
    @staticmethod
    async def get_system_cost(solar_system_id: int):
        if solar_system_id in SystemCost.system_cos_cache:
            return SystemCost.system_cos_cache[solar_system_id]
        res = await SystemCostCacheDBUtils.select_system_cost_by_id(solar_system_id)

        if res:
            res = [res.manufacturing, res.reaction]
            SystemCost.system_cos_cache[solar_system_id] = res
            return res
        else:
            return 0.14, 0.14
