from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image

# kahuna model
from ..service.market_server import PriceService

from ..service.picture_render_server.picture_render import PriceResRender

# global value
ROUGE_PRICE_HELP = ("ojita/ofrt:\n" \
                    "   [物品]:       获得估价。\n"
                    "   [物品] * [数量]: 获得估价。\n")

class TypesPriceEvent():
    @staticmethod
    async def ojita_func(event: AstrMessageEvent, require_str: str):
        item_name = " ".join(event.get_message_str().split(" ")[1:])
        return await TypesPriceEvent.oprice(event, item_name, "jita")

    @staticmethod
    async def ofrt_func(event: AstrMessageEvent, require_str: str):
        item_name = " ".join(event.get_message_str().split(" ")[1:])
        return await TypesPriceEvent.oprice(event, item_name, "frt")

    @staticmethod
    async def oprice(event: AstrMessageEvent, require_str: str, market: str):
        message_str = event.get_message_str()
        if message_str.split(" ")[-1].isdigit():
            quantity = int(message_str.split(" ")[-1])
            item_name = " ".join(message_str.split(" ")[1:-1])
        else:
            item_name = require_str
            quantity = 1

        max_buy, mid_price, min_sell, fuzz_list = PriceService.get_price_rouge(item_name, market)
        if fuzz_list:
            fuzz_rely = (f"物品 {item_name} 不存在于数据库\n"
                         f"你是否在寻找：\n")
            fuzz_rely += '\n'.join(fuzz_list)
            return event.plain_result(fuzz_rely)
        res_path = await PriceResRender.render_price_res_pic(item_name, [max_buy, mid_price, min_sell, fuzz_list])
        chain = [
            Image.fromFileSystem(res_path)
        ]
        return event.chain_result(chain)
