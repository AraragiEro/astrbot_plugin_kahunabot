from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image
from astrbot.core.message.components import Plain

# kahuna model
from ..service.market_server import PriceService
from ..service.market_server.marker import MarketHistory, REGION_FORGE_ID
from ..service.picture_render_server.picture_render import PictureRender
from ..service.sde_service import SdeUtils

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

        # 准备实时价格数据
        item_id, max_buy, mid_price, min_sell, fuzz_list = await PriceService.get_price_rouge(item_name, market)

        # TODO 特别的物品组合map映射
        # 找不到物品时输出模糊匹配结果
        if fuzz_list:
            fuzz_rely = (f"物品 {item_name} 不存在于数据库\n"
                         f"你是否在寻找：\n")
            fuzz_rely += '\n'.join(fuzz_list)
            return event.plain_result(fuzz_rely)

        # 准备历史价格数据
        await MarketHistory.refresh_forge_market_history([item_id])
        history_data = await MarketHistory.get_type_region_history_data(item_id, REGION_FORGE_ID)
        chart_history_data = [[data[0], data[1]] for data in history_data[:365]]

        order_data = await PriceService.get_latest_order(item_id, market)

        quantity_str = ''

        res_path = await PictureRender.render_price_res_pic(
            item_id,
            [max_buy, mid_price, min_sell, fuzz_list],
            chart_history_data
        )
        chain = [
            Image.fromFileSystem(res_path)
        ]
        if quantity > 1:
            quantity_str += f'--------总计--------\n'
            quantity_str += f'sell: {min_sell * quantity:,}\n'
            quantity_str += f'buy: {max_buy * quantity:,}\n'
            quantity_str += f'mid: {mid_price * quantity:,}\n'
            chain += [Plain(quantity_str)]
        return event.chain_result(chain)
