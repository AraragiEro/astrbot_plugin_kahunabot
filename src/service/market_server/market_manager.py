
import asyncio
import time
import threading
from datetime import datetime

from ..database_server.model import MarketOrderCache
from ..database_server.connect import DatabaseConectManager
from ..database_server.utils import RefreshDateUtils
from .marker import Market
from ..character_server.character_manager import CharacterManager
from ..config_server.config import config, update_config
#import Exception
from ...utils import KahunaException

# kahuna logger
from ..log_server import logger

class MarketManager():
    init_status = False
    market_dict = dict()
    monitor_process = None
    refresh_signal_flag = False
    last_refresh_time = None

    @classmethod
    def init(cls):
        cls.init_market()

    @classmethod
    def init_market(cls):
        if not cls.init_status:
            frt_market = Market("frt")
            jita_market = Market("jita")

            try:
                ac_character_id = int(config['EVE']['MARKET_AC_CHARACTER_ID'])
                frt_market.access_character = CharacterManager.get_character_by_id(ac_character_id)
            except:
                logger.error(f"market access character init error")
                return

            cls.market_dict["jita"] = jita_market
            cls.market_dict["frt"] = frt_market
        cls.init_status = True
        logger.info(f"初始化市场. {id(cls)}")

    @classmethod
    def set_ac_character(cls, ac_character_id: int):
        frt_market = Market("frt")
        frt_market.access_character = CharacterManager.get_character_by_id(ac_character_id)
        if not frt_market.check_structure_access():
            raise KahunaException("获取市场数据失败，检查角色名或权限。")
        update_config("EVE", "MARKET_AC_CHARACTER_ID", ac_character_id)

    @classmethod
    def copy_to_cache(cls):
        db = DatabaseConectManager.cache_db()
        with db.atomic():
            MarketOrderCache.delete().execute()
            db.execute_sql("INSERT INTO market_order_cache SELECT * FROM market_order")
            logger.info("copy data to cache complete")

    # 监视器，定时刷新
    @classmethod
    def refresh_market(cls):
        if not RefreshDateUtils.out_of_min_interval('market_order', 20):
            return cls.get_markets_detal()
        else:
            RefreshDateUtils.update_refresh_date('market_order')

        logger.info("开始刷新市场数据。")
        for market in cls.market_dict.values():
            market.get_market_order()
        cls.copy_to_cache()

        log = cls.get_markets_detal()
        logger.info(log)
        return log

    @classmethod
    def get_market_by_type(cls, type: str) -> Market:
        return cls.market_dict.get(type, None)

    @classmethod
    def get_markets_detal(cls) -> str:
        res = {}
        for market in cls.market_dict.values():
            res[market.market_type] = market.get_market_detail()
        refresh_log = ""
        for market, date in res.items():
            refresh_log += (f"{market}:\n"
                            f"  总订单数量：{date[0]} (收单：{date[1]}, 出单：{date[2]}, 物品：{date[3]})\n")
        return refresh_log


# asyncio.run(MarketManager.refresh_per_min(30))
