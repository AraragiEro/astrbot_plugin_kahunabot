from cachetools import TTLCache, cached
from tqdm import tqdm
# from ..database_server.model import MarketPrice as M_MarketPrice, MarketPriceCache as M_MarketPriceCache
from ..database_server.sqlalchemy.kahuna_database_utils import (
    MarketPriceCacheDBUtils, MarketPriceDBUtils
)
from ..evesso_server import eveesi
from ...utils import chunks

# kahuna logger
from ..log_server import logger

class MarketPrice:
    @classmethod
    async def refresh_market_price(cls):
        chunks_size = 1000
        results = await eveesi.markets_prices(log=True)
        # results = [{'adjusted_price': 0.0, 'average_price': 120000.0, 'type_id': 32783}, {'adjusted_price': 36.93619227019693, 'average_price': 33.77, 'type_id': 18}, {'adjusted_price': 38580.38905260794, 'average_price': 78010.36, 'type_id': 32787}, {'adjusted_price': 58170678744.59828, 'type_id': 32788}, {'adjusted_price': 654.67917448883, 'average_price': 982.13, 'type_id': 21}]
        for data in results:
            if 'adjusted_price' not in data:
                data['adjusted_price'] = 0.0
            if  'average_price' not in data:
                data['average_price'] = 0.0

        await MarketPriceDBUtils.delete_all()
        with tqdm(total=int(len(results) / chunks_size), desc="eiv价格写入数据库", unit="chunk", ascii='=-') as pbar:
            for chunk in chunks(results, chunks_size):
                pbar.update()
                try:
                    await MarketPriceDBUtils.insert_many(chunk)
                except Exception as e:
                    # 记录错误和问题数据
                    logger.error(f"插入市场价格数据失败: {str(e)}")
                    # 记录第一条出错的数据以帮助调试
                    if chunk:
                        logger.error(f"错误数据: {chunk}")
                    raise  # 重新抛出异常

        await cls.copy_to_cache()

    @classmethod
    async def copy_to_cache(cls):
        await MarketPriceCacheDBUtils.copy_base_to_cache()
        logger.info("market_price 复制数据到缓存")

    adjusted_price_cache = TTLCache(maxsize=100, ttl=20 * 60)
    @staticmethod
    async def get_adjusted_price_of_typeid(type_id: int):
        if type_id in MarketPrice.adjusted_price_cache:
            return MarketPrice.adjusted_price_cache[type_id]
        market_price = await MarketPriceCacheDBUtils.select_market_price_by_type_id(type_id)

        if not market_price:
            return 0
        else:
            MarketPrice.adjusted_price_cache[type_id] = market_price.adjusted_price
        return market_price.adjusted_price
