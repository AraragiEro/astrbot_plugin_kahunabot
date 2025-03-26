
from ..database_server.model import SystemCost as M_SystemCost, SystemCostCache as M_SystemCostCache
from ..evesso_server.eveesi import industry_systems
from ..database_server.connect import DatabaseConectManager
from ...utils import chunks

# kahuna logger
from ..log_server import logger


class SystemCost:
    @classmethod
    def refresh_system_cost(cls):
        result = industry_systems()

        insert_data = []
        for item in result:
            data = {"solar_system_id": item["solar_system_id"]}
            for cost in item["cost_indices"]:
                data[cost["activity"]] = cost["cost_index"]
            insert_data.append(data)

        db = DatabaseConectManager.cache_db()
        with db.atomic():
            M_SystemCost.delete().execute()
            for chunk in chunks(insert_data, 1000):
                M_SystemCost.insert_many(chunk).execute()

        cls.copy_to_cache()

    @classmethod
    def copy_to_cache(cls):
        db = DatabaseConectManager.cache_db()
        with db.atomic():
            M_SystemCostCache.delete().execute()
            db.execute_sql("INSERT INTO system_cost_cache SELECT * FROM system_cost")
            logger.info("system_cost copy data to cache complete")
