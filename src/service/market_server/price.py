from ..sde_service.utils import SdeUtils
from ..market_server.market_manager import MarketManager

from ...utils import KahunaException

class PriceService:
    @staticmethod
    async def get_price_rouge(item_str: str, market_str: str):
        # 可能的模糊匹配

        if market_str == "jita" or market_str == "frt":
            market = MarketManager.market_dict[market_str]
        else:
            raise KahunaException("market_server not define.")

        # 模糊匹配以及特殊处理
        # 先处理map
        if item_str in SdeUtils.item_map_dict:
            item_str = SdeUtils.item_map_dict[item_str]
        # 找不到id时获取模糊匹配结果并返回给用户
        if (type_id := SdeUtils.get_id_by_name(item_str)) is None:
            fuzz_list = SdeUtils.fuzz_type(item_str)
            return None, None, None, fuzz_list
        else:
            max_buy, min_sell = await market.get_type_order_rouge(type_id)

            # 整理信息
            mid_price = round((max_buy + min_sell) / 2, 2)

            return max_buy, mid_price, min_sell, None




