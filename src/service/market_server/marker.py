from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from peewee import fn
import asyncio
from cachetools import TTLCache, cached
from datetime import datetime, timedelta

from ..database_server.model import MarketOrder as M_MarketOrder, MarketOrderCache as M_MarketOrderCache
from ..database_server import model
from ..database_server.connect import DatabaseConectManager
from ..evesso_server.eveesi import markets_region_orders
from ..evesso_server.eveesi import markets_structures
from ..evesso_server import eveesi
from ..evesso_server.eveutils import find_max_page, get_multipages_result
from ..database_server.utils import RefreshDateUtils
from ..sde_service import SdeUtils

from ...utils import KahunaException

# 查价缓存
from ..database_server.TTL_cache import ROUGE_PRICE_CACHE

# kahuna logger
from ..log_server import logger

REGION_FORGE_ID = 10000002
REGION_VALE_ID = 10000003
JITA_TRADE_HUB_STRUCTURE_ID = 60003760
FRT_4H_STRUCTURE_ID = 1035466617946

class Market:
    market_type = "jita"
    access_character = None

    def __init__(self, market_type="jita"):
        self.market_type = market_type
        if market_type == "jita":
            self.location_id = JITA_TRADE_HUB_STRUCTURE_ID
        else:
            self.location_id = FRT_4H_STRUCTURE_ID

    def set_access_character(self, access_character):
        self.access_character = access_character

    def get_market_order(self):
        if self.market_type == "jita":
            self.get_jita_order()
        if self.market_type == "frt":
            self.get_frt_order()

    def check_structure_access(self):
        res = eveesi.markets_structures(1, self.access_character.ac_token, FRT_4H_STRUCTURE_ID)
        if not res:
            return False
        return True

    def get_frt_order(self):
        if not self.access_character:
            return
        ac_token = self.access_character.ac_token
        max_page = find_max_page(markets_structures, ac_token, FRT_4H_STRUCTURE_ID, begin_page=20, interval=10)
        # with db.atomic() as txn:
        results = get_multipages_result(markets_structures, max_page, self.access_character.ac_token, FRT_4H_STRUCTURE_ID)

        db = DatabaseConectManager.cache_db()
        with db.atomic():
            M_MarketOrder.delete().where(M_MarketOrder.location_id == FRT_4H_STRUCTURE_ID).execute()
            with tqdm(total=len(results), desc="写入数据库", unit="page", ascii='=-') as pbar:
                for i, result in enumerate(results):
                    # result = [order for order in result if order["location_id"] == JITA_TRADE_HUB_STRUCTURE_ID]
                    M_MarketOrder.insert_many(result).execute()
                    pbar.update()

    def get_jita_order(self):
        max_page = find_max_page(markets_region_orders, REGION_FORGE_ID, begin_page=350, interval=50)
        # with db.atomic() as txn:

        logger.info("请求市场。")
        results = get_multipages_result(markets_region_orders, max_page, REGION_FORGE_ID)
        # with ThreadPoolExecutor(max_workers=100) as executor:
        #     futures = [executor.submit(markets_region_orders, page, REGION_FORGE_ID) for page in range(1, max_page+1)]
        #     results = []
        #     count = 1
        #     for future in tqdm(futures, desc="请求市场数据", unit="page"):
        #         result = future.result()
        #         results.append(result)
        #         count += 1

        db = DatabaseConectManager.cache_db()
        with db.atomic():
            M_MarketOrder.delete().where(M_MarketOrder.location_id == JITA_TRADE_HUB_STRUCTURE_ID).execute()
            with tqdm(total=len(results), desc="写入数据库", unit="page", ascii='=-') as pbar:
                for i, result in enumerate(results):
                    result = [order for order in result if order["location_id"] == JITA_TRADE_HUB_STRUCTURE_ID]
                    M_MarketOrder.insert_many(result).execute()
                    pbar.update()

    def get_market_detail(self) -> tuple[int, int, int, int]:
        if self.market_type == "jita":
            target_location = JITA_TRADE_HUB_STRUCTURE_ID
        else:
            target_location = FRT_4H_STRUCTURE_ID

        # 统计总数据数量，并按照is_buy_order进行求和统计
        total_count = (M_MarketOrder
                       .select(fn.COUNT(M_MarketOrder.id))
                       .where(M_MarketOrder.location_id == target_location)
                       .scalar())

        buy_count = (M_MarketOrder
                     .select(fn.COUNT(M_MarketOrder.id))
                     .where((M_MarketOrder.location_id == target_location) &
                            (M_MarketOrder.is_buy_order == True))
                     .scalar())

        sell_count = (M_MarketOrder
                      .select(fn.COUNT(M_MarketOrder.id))
                      .where((M_MarketOrder.location_id == target_location) &
                             (M_MarketOrder.is_buy_order == False))
                      .scalar())

        # 统计不同的类型数量
        distinct_type_count = (M_MarketOrder
                               .select(M_MarketOrder.type_id)
                               .where(M_MarketOrder.location_id == target_location)
                               .distinct()
                               .count())

        return total_count, buy_count, sell_count, distinct_type_count

    order_rouge_cache = TTLCache(maxsize=3000, ttl=20*60)
    @cached(order_rouge_cache)
    def get_type_order_rouge(self, type_id: int) -> tuple[float, float]:
        if self.market_type == "jita":
            target_location = JITA_TRADE_HUB_STRUCTURE_ID
        else:
            target_location = FRT_4H_STRUCTURE_ID
        
        target_id , target_location = type_id, target_location  # replace with actual values
        
        # 获取 is_buy_order=1 的最高价格
        max_price_buy = (M_MarketOrderCache
                         .select(fn.MAX(M_MarketOrderCache.price))
                         .where((M_MarketOrderCache.type_id == target_id) &
                                (M_MarketOrderCache.location_id == target_location) &
                                (M_MarketOrderCache.is_buy_order == True))
                         .scalar())
        
        # 获取 is_buy_order=0 的最低价格
        min_price_sell = (M_MarketOrderCache
                          .select(fn.MIN(M_MarketOrderCache.price))
                          .where((M_MarketOrderCache.type_id == target_id) &
                                 (M_MarketOrderCache.location_id == target_location) &
                                 (M_MarketOrderCache.is_buy_order == False))
                          .scalar())
        if not max_price_buy:
            max_price_buy = 0
        if not min_price_sell:
            min_price_sell = 0
        return float(max_price_buy), float(min_price_sell)

class MarketHistory:
    @classmethod
    async def refresh_vale_market_history(cls, type_id_list: list):
        await cls.refresh_market_history(type_id_list, REGION_VALE_ID)

    @classmethod
    async def refresh_forge_market_history(cls, type_id_list: list):
        await cls.refresh_market_history(type_id_list, REGION_FORGE_ID)

    @classmethod
    async def refresh_market_history(cls, type_id_list: list, region_id: int):
        logger.info(f'刷新历史订单信息。id长度{len(type_id_list)}, region_id:{region_id}')
        with ThreadPoolExecutor(max_workers=10) as executor:
            with tqdm(total=len(type_id_list), desc="创建刷新进程", unit="page", ascii='=-') as pbar:
                futures = []
                for type_id in type_id_list:
                    futures.append(executor.submit(cls.refresh_type_history_in_region, type_id, region_id))
                    await asyncio.sleep(0.05)
                    pbar.update()
            with tqdm(total=len(type_id_list), desc="获取刷新结果", unit="page", ascii='=-') as pbar:
                for future in futures:
                    try:
                        future.result()
                        pbar.update()
                    except Exception as e:
                        logger.error(f"refresh_type_history_in_region error: "
                                     f"{type_id} {SdeUtils.get_name_by_id(type_id)} {e}")

    @classmethod
    def refresh_type_history_in_region(cls, type_id: int, region_id: int):
        result = eveesi.markets_region_history(region_id, type_id)
        if not result:
            return
        [res.update({"type_id": type_id, 'region_id': region_id}) for res in result]

        model.MarketHistory.insert_many(result).on_conflict_ignore().execute()
        RefreshDateUtils.update_refresh_date(cls.get_history_refreshdate_id(type_id, region_id))

    @classmethod
    def get_history_refreshdate_id(cls, type_id: int, region_id: int) -> str:
        history_id =f'markey_history_{type_id}_{region_id}'
        return history_id

    type_region_histpry_data_cache = TTLCache(maxsize=3000, ttl=6 * 60 * 60)
    @classmethod
    @cached(type_region_histpry_data_cache)
    def get_type_region_histpry_data(cls, type_id: int, region_id: int) -> list:
        region_year_data = model.MarketHistory.select().where((model.MarketHistory.type_id == type_id) & (model.MarketHistory.region_id == region_id)).order_by(model.MarketHistory.date.desc())
        region_year_data_list = [[res.date, res.average] for res in region_year_data]

        return region_year_data_list

    @classmethod
    async def get_type_region_history_data_batch(cls, type_id_list: list, region_id: int) -> dict:
        need_refresh_list = [
            tid for tid in type_id_list if RefreshDateUtils.out_of_day_interval(
                cls.get_history_refreshdate_id(tid, region_id), 1
            )
        ]
        if need_refresh_list:
            await cls.refresh_market_history(need_refresh_list, region_id)

        type_region_history_data = {
            tid: cls.get_type_region_histpry_data(tid, region_id) for tid in type_id_list
        }

        return type_region_history_data

    type_history_detale_cache = TTLCache(maxsize=3000, ttl=24 * 60 * 60)
    @classmethod
    @cached(type_history_detale_cache)
    def get_type_history_detale(cls, type_id: int):
        mkhist = model.MarketHistory
        week_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=9)
        month_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=32)
        year_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=366)

        vale_week_data = mkhist.select().where((mkhist.date >= week_ago) & (mkhist.region_id == REGION_VALE_ID) & (mkhist.type_id == type_id)).order_by(mkhist.date.desc())
        vale_month_data = mkhist.select().where((mkhist.date >= month_ago) & (mkhist.region_id == REGION_VALE_ID) & (mkhist.type_id == type_id)).order_by(mkhist.date.desc())
        vale_year_data = mkhist.select().where((mkhist.date >= year_ago) & (mkhist.region_id == REGION_VALE_ID) & (mkhist.type_id == type_id)).order_by(mkhist.date.desc())
        vale_week_data_list = [[res.average, res.highest, res.lowest, res.order_count, res.volume] for res in vale_week_data]
        vale_month_data_list = [[res.average, res.highest, res.lowest, res.order_count, res.volume] for res in vale_month_data]
        vale_year_data_list = [[res.average, res.highest, res.lowest, res.order_count, res.volume] for res in vale_year_data]

        forge_week_data = mkhist.select().where((mkhist.date >= week_ago) & (mkhist.region_id == REGION_FORGE_ID) & (mkhist.type_id == type_id)).order_by(mkhist.date.desc())
        forge_month_data = mkhist.select().where((mkhist.date >= month_ago) & (mkhist.region_id == REGION_FORGE_ID) & (mkhist.type_id == type_id)).order_by(mkhist.date.desc())
        forge_year_data = mkhist.select().where((mkhist.date >= year_ago) & (mkhist.region_id == REGION_FORGE_ID) & (mkhist.type_id == type_id)).order_by(mkhist.date.desc())
        forge_week_data_list = [[res.average, res.highest, res.lowest, res.order_count, res.volume] for res in forge_week_data]
        forge_month_data_list = [[res.average, res.highest, res.lowest, res.order_count, res.volume] for res in forge_month_data]
        forge_year_data_list = [[res.average, res.highest, res.lowest, res.order_count, res.volume] for res in forge_year_data]

        vale_res ={}
        forge_res = {}

        count = 0
        flow = 0
        highest_average = 0
        lowest_average = 0
        total_volume = 0
        for data in vale_week_data_list:
            flow += data[0] * data[4]
            count += 1
            total_volume += data[4]
            highest_average += data[1]
            lowest_average += data[2]
        vale_res.update({
            'weekflow': flow,
            'week_highset_aver': highest_average / count if count else 0,
            'week_lowest_aver': lowest_average / count if count else 0,
            'week_volume': total_volume
        })

        count = 0
        flow = 0
        highest_average = 0
        lowest_average = 0
        total_volume = 0
        for data in vale_month_data_list:
            flow += data[0] * data[4]
            count += 1
            total_volume += data[4]
            highest_average += data[1]
            lowest_average += data[2]
        vale_res.update({
            'monthflow': flow,
            'month_highset_aver': highest_average / count if count else 0,
            'month_lowest_aver': lowest_average / count if count else 0,
            'month_volume': total_volume
        })

        count = 0
        flow = 0
        highest_average = 0
        lowest_average = 0
        total_volume = 0
        for data in vale_year_data_list:
            flow += data[0] * data[4]
            count += 1
            total_volume += data[4]
            highest_average += data[1]
            lowest_average += data[2]
        vale_res.update({
            'yearflow': flow,
            'year_highset_aver': highest_average / count if count else 0,
            'year_lowest_aver': lowest_average / count if count else 0,
            'year_volume': total_volume
        })

        count = 0
        flow = 0
        highest_average = 0
        lowest_average = 0
        total_volume = 0
        for data in forge_week_data_list:
            flow += data[0] * data[4]
            count += 1
            total_volume += data[4]
            highest_average += data[1]
            lowest_average += data[2]
        forge_res.update({
            'weekflow': flow,
            'week_highset_aver': highest_average / count if count else 0,
            'week_lowest_aver': lowest_average / count if count else 0,
            'week_volume': total_volume
        })

        count = 0
        flow = 0
        highest_average = 0
        lowest_average = 0
        total_volume = 0
        for data in forge_month_data_list:
            flow += data[0] * data[4]
            count += 1
            total_volume += data[4]
            highest_average += data[1]
            lowest_average += data[2]
        forge_res.update({
            'monthflow': flow,
            'month_highset_aver': highest_average / count if count else 0,
            'month_lowest_aver': lowest_average / count if count else 0,
            'month_volume': total_volume
        })

        count = 0
        flow = 0
        highest_average = 0
        lowest_average = 0
        total_volume = 0
        for data in forge_year_data_list:
            flow += data[0] * data[4]
            count += 1
            total_volume += data[4]
            highest_average += data[1]
            lowest_average += data[2]
        forge_res.update({
            'yearflow': flow,
            'year_highset_aver': highest_average / count if count else 0,
            'year_lowest_aver': lowest_average / count if count else 0,
            'year_volume': total_volume
        })

        return vale_res, forge_res


