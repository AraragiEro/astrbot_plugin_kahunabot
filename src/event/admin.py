# import logger
from concurrent.futures import ThreadPoolExecutor
import asyncio
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Image, BaseMessageComponent, Plain

# kahuna model
from ..service.asset_server import AssetManager
from ..service.character_server import CharacterManager
from ..service.industry_server.industry_analyse import IndustryAnalyser
from ..service.user_server.user_manager import UserManager
from ..service.evesso_server.eveesi import characters_character
from ..service.market_server import MarketManager, PriceService
from ..service.market_server.marker import MarketHistory
from ..service.asset_server.asset_container import AssetContainer
from ..service.industry_server.industry_config import IndustryConfigManager, BPManager
from ..service.industry_server.structure import StructureManager
from ..service.industry_server.industry_manager import IndustryManager
from ..service.industry_server.industry_advice import IndustryAdvice
from ..service.sde_service.utils import SdeUtils
from ..service.feishu_server.feishu_kahuna import FeiShuKahuna
from ..service.log_server import logger
from ..service.picture_render_server.picture_render import PriceResRender
from ..service.config_server.config import config, update_config

from ..utils import KahunaException

class AdminEvent:
    @staticmethod
    async def setpubliccostplan(event: AstrMessageEvent, user_qq: int, plan_name: str):
        user = UserManager.get_user(user_qq)
        if plan_name not in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")

        update_config('APP', 'COST_PLAN_USER', user_qq)
        update_config('APP', 'COST_PLAN_NAME', plan_name)

        return event.plain_result(f'已设置{user_qq} 的 {plan_name} 计划为公共成本计算基准。')

