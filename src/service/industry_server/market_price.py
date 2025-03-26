
from ..database_server.model import MarketPrice as M_MarketPrice, MarketPriceCache as M_MarketPriceCache
from ..evesso_server.eveesi import markets_prices
from ..database_server.connect import DatabaseConectManager
from ...utils import chunks

# kahuna logger
from ..log_server import logger

class MarketPrice:
    @classmethod
    def refresh_market_price(cls):
        results = markets_prices()
        db = DatabaseConectManager.cache_db()
        with db.atomic():
            M_MarketPrice.delete().execute()
            for chunk in chunks(results, 1000):
                M_MarketPrice.insert_many(chunk).execute()

        cls.copy_to_cache()

    @classmethod
    def copy_to_cache(cls):
        db = DatabaseConectManager.cache_db()
        with db.atomic():
            M_MarketPriceCache.delete().execute()
            db.execute_sql("INSERT INTO market_price_cache SELECT * FROM market_price")
            logger.info("market_price copy data to cache complete")

