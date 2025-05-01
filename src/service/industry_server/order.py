from typing import Any, Coroutine

from ..evesso_server import eveesi
from ..log_server import logger
from ..character_server.character_manager import Character, CharacterManager
from ..user_server.user_manager import User, UserManager
from ..evesso_server.eveutils import find_max_page, get_multipages_result, parse_iso_datetime
from ..sde_service import SdeUtils
from ..market_server.marker import FRT_4H_STRUCTURE_ID, JITA_TRADE_HUB_STRUCTURE_ID
from ..market_server.market_manager import MarketManager
from ..industry_server.structure import StructureManager
from ...utils import get_beijing_utctime
from ..database_server.sqlalchemy.kahuna_database_utils import (
    OrderHistoryDBUtils,
    RefreshDataDBUtils
)

class OrderManager:
    def __init__(self):
        pass

    async def get_character_orders(self, character: Character):
        results = await eveesi.characters_character_orders(await character.ac_token, character.character_id)
        for res in results:
            if 'is_buy_order' not in res:
                res.update({
                    'escrow': 0.0,
                    'is_buy_order': False,
                    'min_volume': 0
                })
            res.update({
                'owner_id': character.character_id,
                "issued": get_beijing_utctime(parse_iso_datetime(res['issued']))
            })
        return results

    async def get_order_of_user(self, user: User):
        character_list = CharacterManager.get_all_characters_of_user(user.user_qq)
        orders = []
        for character in character_list:
            orders.extend(await self.get_character_orders(character))
        return orders

    async def refresh_character_order_history(self, character: Character):
        max_page = await find_max_page(
            eveesi.characters_character_orders_history,
            await character.ac_token,
            character.character_id,
            begin_page=1,
            interval=2
        )
        results = await get_multipages_result(
            eveesi.characters_character_orders_history,
            max_page,
            await character.ac_token,
            character.character_id
        )

        for result in results:
            for data in result:
                data.update({
                    'owner_id': character.character_id,
                    "issued": get_beijing_utctime(parse_iso_datetime(data['issued']))
                })
                if 'is_buy_order' not in data:
                    data.update({
                        'escrow': 0.0,
                        'is_buy_order': False,
                        'min_volume': 0
                    })
            await OrderHistoryDBUtils.insert_many_ignore_conflict(result)

        logger.info(f'{character.character_name} 刷新订单 {max_page} 页')

    async def refresh_order_history_of_user(self, user: User, force=False):
        if not force and not await RefreshDataDBUtils.out_of_day_interval(f'order_history_{user.user_qq}', 1):
            return
        character_list = CharacterManager.get_all_characters_of_user(user.user_qq)
        for character in character_list:
            await self.refresh_character_order_history(character)

        await RefreshDataDBUtils.update_refresh_date(f'order_history_{user.user_qq}')

    async def refresh_all_order(self, force=False):
        user_list = UserManager.get_users_list()
        for user in user_list:
            await self.refresh_order_history_of_user(user, force=force)

    async def get_order_history_of_user(self, user: User):
        character_list = CharacterManager.get_all_characters_of_user(user.user_qq)

        return await OrderHistoryDBUtils.select_order_history_by_owner_id_list(
            [character.character_id for character in character_list]
        )

    async def filt_sell_order_of_location_id(self, order_data: list[dict], location_id: int) -> list[Any] | None:
        if location_id not in {FRT_4H_STRUCTURE_ID, JITA_TRADE_HUB_STRUCTURE_ID}:
            logger.error("暂不支持除联盟市场和jita市场的订单统计")
            return []
        if location_id == FRT_4H_STRUCTURE_ID:
            market = MarketManager.get_market_by_type('frt')
        else:
            market = MarketManager.get_market_by_type('jita')

        structure = await StructureManager.get_structure(location_id)
        if structure:
            structure_name = structure.name
        else:
            structure_name = 'unknown structure'

        sell_order = [{
            'type_id': order['type_id'],
            'name': SdeUtils.get_name_by_id(order['type_id']),
            'icon': '',
            'structure_name': structure_name,
            'volume_total': order['volume_total'],
            'volume_remain': order['volume_remain'],
            'price': order['price'],
            'min_price': (await market.get_type_order_rouge(order['type_id']))[1],
            'issued': order['issued'],
            'duration': order['duration']
        } for order in order_data if not order['is_buy_order'] and order['location_id'] == location_id]
        sell_order.sort(key=lambda x: x['type_id'], reverse=False)

        res = {}
        for order in sell_order:
            if order['type_id'] not in res:
                res[order['type_id']] = order
                continue
            if order['price'] < res[order['type_id']]['price']:
                res[order['type_id']] = order
        res = [order for order in res.values()]
        res.sort(key=lambda x: x['type_id'], reverse=False)
        return res

order_manager = OrderManager()