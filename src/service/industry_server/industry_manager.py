import asyncio

from .running_job import RunningJobOwner
from .system_cost import SystemCost
from .market_price import MarketPrice
from ..character_server.character_manager import CharacterManager
# from ..database_server.utils import RefreshDateUtils
from ..database_server.sqlalchemy.kahuna_database_utils import (
    RefreshDataDBUtils
)

# kahuna logger
from ..log_server import logger

class IndustryManager:
    @classmethod
    async def refresh_running_status(cls):
        if not await RefreshDataDBUtils.out_of_min_interval('running_job', 10):
            return

        logger.info("刷新运行中job.")
        character_list = [character for character in CharacterManager.character_dict.values()]

        corp_list_id_list = []
        exist_corp_set = set()
        for character in character_list:
            if character.director and character.corp_id not in exist_corp_set:
                corp_list_id_list.append((character.corp_id, character))
                exist_corp_set.add(character.corp_id)

        for character in character_list:
            await RunningJobOwner.refresh_character_running_job(character)
        for corp_id, character in corp_list_id_list:
            await RunningJobOwner.refresh_corp_running_job(corp_id, character)

        await RunningJobOwner.copy_to_cache()

        await RefreshDataDBUtils.update_refresh_date('running_job')
        logger.info("job 刷新完成")

    @classmethod
    async def refresh_system_cost(cls):
        if not await RefreshDataDBUtils.out_of_hour_interval('system_cost', 1):
            return


        logger.info('刷新星系系数')
        await SystemCost.refresh_system_cost()

        logger.info('刷新星系系数 完成')
        await RefreshDataDBUtils.update_refresh_date('system_cost')

    @classmethod
    async def refresh_market_price(cls):
        if not await RefreshDataDBUtils.out_of_hour_interval('market_price', 2):
            return

        logger.info("开始刷新eiv价格。")
        await MarketPrice.refresh_market_price()

        logger.info("刷新eiv价格 完成。")
        await RefreshDataDBUtils.update_refresh_date('market_price')
    # 调起工业分析
    # @classmethod
    # def create_plan_analyser(cls, user, plan_name: str):
    #     if plan_name not in user.user_data.plan:
    #         raise KahunaException("plan not found.")
    #     if plan_name in IndustryAnalyser.analyser_cache:
    #         return IndustryAnalyser.analyser_cache[plan_name]
    #     analyser = IndustryAnalyser(user.user_qq, "work")
    #     # 配置匹配器
    #     bp_matcher = IndustryConfigManager.get_matcher_of_user_by_name(user.user_data.plan[plan_name]["bp_matcher"], user.user_qq)
    #     st_matcher = IndustryConfigManager.get_matcher_of_user_by_name(user.user_data.plan[plan_name]["st_matcher"], user.user_qq)
    #     prod_block_matcher = IndustryConfigManager.get_matcher_of_user_by_name(user.user_data.plan[plan_name]["prod_block_matcher"], user.user_qq)
    #     analyser.set_matchers(bp_matcher, st_matcher, prod_block_matcher)
    #     # 导入计划表
    #     plan = user.user_data.plan[plan_name]["plan"]
    #     work_list = [[product, quantity] for product, quantity in plan.items()]
    #     await analyser.analyse_progress_work_type(work_list)
    #
    #     IndustryAnalyser.analyser_cache[plan_name] = analyser

