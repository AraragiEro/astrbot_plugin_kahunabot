# import logger
import json
import os
from concurrent.futures import ThreadPoolExecutor
import asyncio
from datetime import datetime, timedelta

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
from ..service.config_server.config import config

from ..utils import (
    KahunaException,
    get_user_tmp_cache_prefix,
    get_beijing_utctime,
    get_debug_qq
)
from ..utils.path import TMP_PATH

calculate_lock = asyncio.Lock()
async def try_acquire_lock(lock, timeout=0.01):
    """尝试非阻塞地获取锁"""
    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False

def print_name_fuzz_list(event: AstrMessageEvent, type_name: str):
    fuzz_list = SdeUtils.fuzz_type(type_name, list_len=10)
    if fuzz_list:
        fuzz_rely = (f"你是否在寻找：\n")
        fuzz_rely += '\n'.join(fuzz_list)
        return event.plain_result(fuzz_rely)

def get_user(event: AstrMessageEvent):
    if get_debug_qq():
        user_qq = get_debug_qq()
    else:
        user_qq = int(event.get_sender_id())
    
    return user_qq

class AssetEvent():
    @staticmethod
    def get_owner_id(owner_type: str, character_name: str, character) -> int:
        if owner_type == "corp":
            character_info = characters_character(character.character_id)
            owner_id = int(character_info["corporation_id"])
        elif owner_type == "character":
            owner_id = character.character_id
        else:
            raise KahunaException("owner_type must be 'corp' or 'character'")

        return owner_id

    @classmethod
    def refall(cls, event: AstrMessageEvent):
        AssetManager.refresh_all_asset()

        return event.plain_result("执行完成")

    @staticmethod
    def owner_add(event: AstrMessageEvent, owner_type: str, character_name: str):
        user_qq = get_user(event)
        character = CharacterManager.get_character_by_name_qq(character_name, user_qq)

        owner_id = AssetEvent.get_owner_id(owner_type, character_name, character)

        asset = AssetManager.create_asset(user_qq, owner_type, owner_id, character)
        return event.plain_result(f"库存已成功创建。\n"
                                  f"库存条目 {asset.asset_item_count}")

    @staticmethod
    def owner_refresh(event: AstrMessageEvent, owner_type: str, character_name: str):
        user_qq = get_user(event)
        character = CharacterManager.get_character_by_name_qq(character_name, user_qq)

        owner_id = AssetEvent.get_owner_id(owner_type, character_name, character)

        asset = AssetManager.refresh_asset(owner_type, owner_id)
        return event.plain_result("刷新完成")

    @staticmethod
    def container_add(event: AstrMessageEvent, location_id: int, location_flag: str, target_qq: int, container_name: str):
        user_qq = get_user(event)

        main_character_id = UserManager.get_main_character_id(user_qq)
        main_character = CharacterManager.get_character_by_id(main_character_id)
        container = AssetManager.add_container(target_qq, location_id, location_flag, container_name, user_qq, main_character.ac_token)
        print_info = (f"已授权 {target_qq} 使用属于 {user_qq} 的库存: {location_id}。\n")
        return event.plain_result(print_info)

    @staticmethod
    def container_ls(event: AstrMessageEvent):
        user_qq = get_user(event)

        print_str = "你可访问以下库存：\n"
        for container in AssetManager.container_dict.values():
            if (AssetContainer.operater_has_container_permission(user_qq, container.asset_owner_id) and
                user_qq == container.asset_owner_qq):
                logger.info(f'{user_qq} == container.asset_owner_qq')
                print_str += f"{container}\n"
        return event.plain_result(print_str)

    @staticmethod
    def container_find(event: AstrMessageEvent, secret_type: str):
        user_qq = get_user(event)
        secret_type = " ".join(event.get_message_str().split(" ")[3:])
        if SdeUtils.maybe_chinese(secret_type):
            type_id = SdeUtils.get_id_by_name(secret_type)
        else:
            type_id = SdeUtils.get_id_by_name(secret_type)
        if not type_id:
            return print_name_fuzz_list(event, secret_type)

        main_character_id = UserManager.get_main_character_id(user_qq)
        main_character = CharacterManager.get_character_by_id(main_character_id)
        container_info = AssetContainer.find_container(secret_type, user_qq, main_character)

        print_info = f"找到{len(container_info)}个符合条件的库存空间。\n"
        for container in container_info:
            print_info += (f"\n建筑名：{container['name']} 数量：{container['exist_quantity']}\n"
                           f"建筑类型：{container['structure_type']}\n"
                           f"星系：{container['system']}\n"
                           f"添加库存指令：.asset container add {container['location_id']} {container['location_flag']} [授权目标qq] [库存空间别名]\n")
        return event.plain_result(print_info)

    @staticmethod
    def container_settag(event: AstrMessageEvent, location_id_list: str, tag: str):
        user_qq = get_user(event)
            
        location_id_list = [int(lid) for lid in location_id_list.split(",")]
        success_list = AssetManager.set_container_tag([(user_qq, location_id) for location_id in location_id_list], tag)

        print_str = "成功设置以下库存tag：\n"
        for container in success_list:
            print_str += f"{container.asset_location_id}: {container.tag}\n"


        return event.plain_result(print_str)


class IndsEvent:
    @staticmethod
    def matcher_create(event: AstrMessageEvent, matcher_name: str, matcher_type: str):
        if matcher_type not in IndustryConfigManager.matcher_type_set:
            raise KahunaException(f"matcher_type {matcher_type} must be {IndustryConfigManager.matcher_type_set}")
        matcher = IndustryConfigManager.add_matcher(matcher_name, int(event.get_sender_id()), matcher_type)

        return event.plain_result(f"已为用户 {int(event.get_sender_id())} 添加适配器 {matcher.matcher_name}")

    @staticmethod
    def matcher_del(event: AstrMessageEvent, matcher_name: str):
        delete_matcher = IndustryConfigManager.delete_matcher(matcher_name, int(event.get_sender_id()))
        return event.plain_result(f"已删除工业系数匹配器： {delete_matcher.matcher_name}")

    @staticmethod
    def matcher_ls(event: AstrMessageEvent):
        matcher_list = IndustryConfigManager.get_user_matcher(int(event.get_sender_id()))

        res_str = f"您可以使用以下工业系数匹配器：\n"
        for matcher in matcher_list:
            res_str += f"  {matcher.matcher_type} type matcher: {matcher.matcher_name}\n"

        return event.plain_result(res_str)

    @staticmethod
    def matcher_info(event: AstrMessageEvent, matcher_name: str):
        matcher = IndustryConfigManager.matcher_dict.get(matcher_name, None)
        if not matcher or matcher.user_qq != int(event.get_sender_id()):
            return event.plain_result("匹配器不存在。")

        res = f"{matcher.matcher_name}: type:{matcher.matcher_type}\n"

        for matcher_types, matcher_datas in matcher.matcher_data.items():
            prefix = ""
            res += f"{prefix}├── {matcher_types}:\n"
            for matcher_key, matcher_data in matcher_datas.items():
                prefix = "├── "
                if matcher.matcher_type == "structure":
                    matcher_data = StructureManager.get_structure(matcher_data).name
                res += f"{prefix}├── {matcher_key}: {matcher_data}\n"

        return event.plain_result(res)

    @staticmethod
    def matcher_set(event: AstrMessageEvent, matcher_name:str, matcher_key_type: str):
        config_data = event.get_message_str().split(" ")[5:]

        matcher = IndustryConfigManager.get_matcher_of_user_by_name(matcher_name, int(event.get_sender_id()))
        if not matcher:
            return event.plain_result("未找到匹配器，可用指令 .Inds matcher ls 查询可用匹配器")

        if matcher_key_type not in matcher.matcher_data:
            return event.plain_result(f"matcher_key_type匹配器关键字必须为: {[matcher.matcher_data.keys()]}")

        def check_match_key(match_key):
            # 确认信息方法
            if matcher_key_type == "bp" and not BPManager.get_bp_id_by_pbpname(matcher_key):
                return False, event.plain_result("{matcher_key}: 不存在的蓝图，请先使用sde type指令确认物品属性")
            elif matcher_key_type == "market_group" and SdeUtils.get_market_groupid_by_name(matcher_key) not in SdeUtils.get_market_group_tree():
                return False, event.plain_result(f"{matcher_key}: 不存在的市场类别，请先使用sde type指令确认物品属性")
            elif matcher_key_type == "group" and not SdeUtils.get_groupid_by_groupname(matcher_key):
                return False, event.plain_result(f"{matcher_key}: 不存在的组类别，请先使用sde type指令确认物品属性")
            elif matcher_key_type == "meta" and not SdeUtils.get_metadid_by_metaname(matcher_key):
                return False, event.plain_result(f"{matcher_key}: 不存在的组类别，请先使用sde type指令确认物品属性")
            return True, None

        if matcher.matcher_type == "bp" and len(config_data) >= 3 and config_data[-2].isdigit() and config_data[-1].isdigit():
            matcher_key = " ".join(config_data[:-2])
            mater_eff = float(f"{1 - (int(config_data[-2]) / 100):.2f}")
            time_eff = float(f"{1 - (int(config_data[-1]) / 100):.2f}")

            # 确认信息无误
            matche_key_check, res = check_match_key(matcher_key)
            if not matche_key_check:
                return res
            # 如果关键词类型为bp，标准化为英文
            if matcher_key_type == "bp":
                matcher_key = SdeUtils.get_name_by_id(SdeUtils.get_id_by_name(matcher_key))

            matcher.matcher_data[matcher_key_type][matcher_key] = {"mater_eff": mater_eff, "time_eff": time_eff}
            matcher.insert_to_db()
            return event.plain_result("已配置，可以使用Inds matcher info 查看详情。")

        elif matcher.matcher_type == "structure" and len(config_data) >= 2 and config_data[-1].isdigit():
            matcher_key = " ".join(config_data[:-1])
            structure_id = int(config_data[-1])

            # 确认信息无误
            matche_key_check, res = check_match_key(matcher_key)
            if not matche_key_check:
                return res
            if matcher_key_type == "bp":
                matcher_key = SdeUtils.get_name_by_id(SdeUtils.get_id_by_name(matcher_key))

            character = CharacterManager.get_character_by_id(UserManager.get_main_character_id(int(event.get_sender_id())))
            structure = StructureManager.get_structure(structure_id, character.ac_token)
            if not structure:
                return event.plain_result("获取建筑信息失败")

            matcher.matcher_data[matcher_key_type][matcher_key] = structure.structure_id
            matcher.insert_to_db()

            return event.plain_result("已配置，可以使用Inds matcher info 查看详情。")

        elif matcher.matcher_type == "prod_block" and len(config_data) >= 2:
            matcher_key = " ".join(config_data[:-1])
            block_level = int(config_data[-1])

            # 确认信息无误
            matche_key_check, res = check_match_key(matcher_key)
            if not matche_key_check:
                return res
            if matcher_key_type == "bp":
                matcher_key = SdeUtils.get_name_by_id(SdeUtils.get_id_by_name(matcher_key))

            matcher.matcher_data[matcher_key_type][matcher_key] = block_level
            matcher.insert_to_db()

            return event.plain_result("已配置，可以使用Inds matcher info 查看详情。")

        return event.plain_result('matcher_type 未匹配分支。')

    @staticmethod
    def matcher_unset(event: AstrMessageEvent, matcher_name:str, matcher_key_type: str):
        config_data = event.get_message_str().split(" ")[5:]

        matcher = IndustryConfigManager.get_matcher_of_user_by_name(matcher_name, int(event.get_sender_id()))
        if not matcher:
            return event.plain_result("未找到匹配器，可用指令 .Inds matcher ls 查询可用匹配器")

        if matcher.matcher_type in IndustryConfigManager.matcher_type_set:
            matcher_key = " ".join(config_data[:-1])

            if matcher_key_type not in matcher.matcher_data:
                return event.plain_result(f"matcher_key_type匹配器关键字必须为: {[matcher.matcher_data.keys()]}")
            if matcher_key in matcher.matcher_data[matcher_key_type]:
                matcher.matcher_data[matcher_key_type].pop(matcher_key)
                matcher.insert_to_db()
            return event.plain_result("已配置，可以使用Inds matcher info 查看详情。")
        return event.plain_result('matcher_type 未匹配分支。')

    @staticmethod
    def structure_ls(event: AstrMessageEvent):
        structure_list = StructureManager.get_all_structure()
        print_list = []
        for structure in structure_list:
            print_list.append(f"id: {structure.structure_id}\n"
                              f"Type: {SdeUtils.get_name_by_id(structure.type_id)}\n"
                              f"Name: {structure.name}\n"
                              f"rig: {structure.mater_rig_level}-{structure.time_rig_level}\n")
        return event.plain_result("\n".join(print_list))

    @staticmethod
    def structure_info(event: AstrMessageEvent, structure_id: int):
        character = CharacterManager.get_character_by_id(UserManager.get_main_character_id(int(event.get_sender_id())))
        structure = StructureManager.get_structure(structure_id, character.ac_token)
        return event.plain_result(
            f"name: {structure.name}\n"
            f"id: {structure.structure_id}\n"
            f"type: {SdeUtils.get_name_by_id(structure.type_id)}\n"
            f"mater_rig_level: {structure.mater_rig_level}\n"
            f"time_rig_level: {structure.time_rig_level}\n"
            f"system: {structure.system}\n"
        )

    @staticmethod
    def structure_set(event: AstrMessageEvent, structure_id: int, mater_rig_level: int, time_rig_level: int):
        if mater_rig_level < 0 or mater_rig_level > 2 \
            or time_rig_level < 0 or time_rig_level > 2:
            return event.plain_result("rig_level must be 0, 1 or 2")
        character = CharacterManager.get_character_by_id(UserManager.get_main_character_id(int(event.get_sender_id())))
        structrue = StructureManager.get_structure(structure_id, character.ac_token)
        structrue.mater_rig_level = mater_rig_level
        structrue.time_rig_level = time_rig_level
        structrue.insert_to_db()

        return event.plain_result(
            f"{structrue.name} {SdeUtils.get_name_by_id(structrue.type_id)} 已配置 "
            f"材料插等级{mater_rig_level} 时间插等级{time_rig_level}"
        )

    @staticmethod
    def plan_setprod(event: AstrMessageEvent, plan_name: str):
        user_qq = get_user(event)
        config_data = event.get_message_str().split(" ")[4:]
        prod_name = " ".join(config_data[:-1])
        quantity = config_data[-1]
        if not quantity.isdigit():
            raise KahunaException("quantity must be digit")

        quantity = int(quantity)
        if not SdeUtils.get_id_by_name(prod_name):
            return print_name_fuzz_list(event, prod_name)
        user = UserManager.get_user(user_qq)
        user.set_plan_product(plan_name, prod_name, quantity)
        res_str = (f"计划已添加，当前计划：\n"
                   f"{plan_name}:\n")
        for index, plan in enumerate(user.user_data.plan[plan_name]["plan"]):
            res_str += f"  |-{index + 1}.{plan[0]}: {plan[1]}\n"

        return event.plain_result(res_str)

    @staticmethod
    def plan_setcycletime(event: AstrMessageEvent, plan_name:str, time_type: str, hour: int):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        if time_type == 'reac':
            user.set_reac_cycle_time(plan_name, hour)
        elif time_type == 'manu':
            user.set_manu_cycle_time(plan_name, hour)
        else:
            return event.plain_result(f"args: [plan name] [reac/manu] [hour]")

        return event.plain_result(f"执行完成。计划{plan_name}的{time_type}最长流程时间已设置为{hour}小时")

    @staticmethod
    def plan_set_line(event:AstrMessageEvent, plan_name:str, line_type: str, line_num:int):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        if line_type == 'reac':
            user.set_reac_line_num(plan_name, line_num)
        elif line_type == 'manu':
            user.set_manu_line_num(plan_name, line_num)
        else:
            return event.plain_result(f"args: [plan name] [read/manu] [line num]")

        return event.plain_result(f"执行完成。计划{plan_name}的{line_type}反应线设为{line_num}")

    @staticmethod
    def plan_create(event: AstrMessageEvent, plan_name: str,
                    bp_matcher_name: str, st_matcher_name: str, prod_block_matcher_name: str):
        user_qq = get_user(event)
        bp_matcher = IndustryConfigManager.get_matcher_of_user_by_name(bp_matcher_name, user_qq)
        st_matcher = IndustryConfigManager.get_matcher_of_user_by_name(st_matcher_name, user_qq)
        prod_block_matcher = IndustryConfigManager.get_matcher_of_user_by_name(prod_block_matcher_name, user_qq)
        user = UserManager.get_user(user_qq)
        user.create_plan(plan_name, bp_matcher, st_matcher, prod_block_matcher)

        return event.plain_result("计划已创建")

    @staticmethod
    def plan_ls(event: AstrMessageEvent, plan_name: str):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)

        plan_detail = user.user_data.get_plan_detail(plan_name)

        return event.plain_result(plan_detail)

    @staticmethod
    def plan_delprod(event: AstrMessageEvent, plan_name: str, index_list: str):
        user_qq = get_user(event)
        index_list = index_list.split(",")
        index_list = [int(index) for index in index_list]
        index_list.sort(reverse=True)

        user = UserManager.get_user(user_qq)
        for index in index_list:
            user.delete_plan_prod(plan_name, index - 1)

        return event.plain_result("执行完成")

    @staticmethod
    def plan_changeindex(event: AstrMessageEvent, plan_name: str, index: int, target_index: int):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)

        if not plan_name in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")

        plan_len = len(user.user_data.plan[plan_name]["plan"])
        if index < 1 or index > plan_len:
            raise KahunaException(f"index {index} out of range")
        if target_index < 1 or target_index > plan_len:
            raise KahunaException(f"target_index {target_index} out of range")

        plan = user.user_data.plan[plan_name]["plan"].pop(index - 1)
        user.user_data.plan[plan_name]["plan"].insert(target_index - 1, plan)
        user.insert_to_db()

        return event.plain_result("执行完成。")

    @staticmethod
    def plan_delplan(event: AstrMessageEvent, plan_name: str):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        user.delete_plan(plan_name)

        return event.plain_result("执行完成")

    @staticmethod
    def plan_hidecontainer(event: AstrMessageEvent, plan_name: str, container_id: int):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        if plan_name not in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")

        user.add_container_block(plan_name, container_id)
        return event.plain_result("执行完成")

    @staticmethod
    def plan_unhidecontainer(event: AstrMessageEvent, plan_name: str, container_id: int):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        if plan_name not in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")

        user.del_container_block(plan_name, container_id)
        return event.plain_result("执行完成")

    @staticmethod
    async def rp_plan(event: AstrMessageEvent, plan_name: str):
        user_qq = get_user(event)
        
        user = UserManager.get_user(user_qq)
        if plan_name not in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")

        with ThreadPoolExecutor(max_workers=1) as executor:
            analyser = IndustryAnalyser.get_analyser_by_plan(user, plan_name)
            analyser.bp_block_level = 2
            future = executor.submit(analyser.get_work_tree_data)
            while not future.done():
                await asyncio.sleep(1)
            report = future.result()

        spreadsheet = FeiShuKahuna.create_user_plan_spreadsheet(user_qq, plan_name)
        FeiShuKahuna.create_default_spreadsheet(spreadsheet)
        work_tree_sheet = FeiShuKahuna.get_worktree_sheet(spreadsheet)
        FeiShuKahuna.output_work_tree(work_tree_sheet, report['work'])
        material_sheet = FeiShuKahuna.get_material_sheet(spreadsheet)
        FeiShuKahuna.output_material_tree(material_sheet, report['material'])
        work_flow_sheet = FeiShuKahuna.get_workflow_sheet(spreadsheet)
        FeiShuKahuna.output_work_flow(work_flow_sheet, report['work_flow'])
        logistic_sheet = FeiShuKahuna.get_logistic_sheet(spreadsheet)
        FeiShuKahuna.output_logistic_plan(logistic_sheet, report['logistic'])

        # 删除不可写入json的多余部分
        report.pop('logistic')
        plan_cache = get_user_tmp_cache_prefix(user_qq) + f'{plan_name}_' + 'plan_report.json'
        with open(os.path.join(TMP_PATH, plan_cache), 'w') as file:
            cache_dict = {
                'date': get_beijing_utctime(datetime.now()).isoformat(),
                'data': report
            }
            json.dump(cache_dict, file, indent=4)

        return event.plain_result(f"执行完成, 当前计划蓝图分解:{work_tree_sheet.url}")

    @staticmethod
    async def rp_t2mk(event: AstrMessageEvent, plan_name: str):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        if plan_name not in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")
        # 
        # t2_ship_list = SdeUtils.get_t2_ship()
        # t2_plan = [[ship, 1] for ship in t2_ship_list]
        # 
        # t2_cost_data = IndustryAnalyser.get_cost_data(user, plan_name, t2_plan)
        with ThreadPoolExecutor(max_workers=1) as executor:
            t2_ship_list = SdeUtils.get_t2_ship()
            t2_ship_id_list = [SdeUtils.get_id_by_name(name) for name in t2_ship_list]
            await MarketHistory.refresh_vale_market_history(t2_ship_id_list)

            # t2mk_data = IndustryAdvice.t2_ship_advice_report(user, plan_name)
            future = executor.submit(IndustryAdvice.advice_report, user, plan_name, t2_ship_list)
            while not future.done():
                await asyncio.sleep(1)
            t2mk_data = future.result()

        asset_dict = {}
        sell_container_list = AssetContainer.get_contain_id_by_qq_tag(user_qq, 'sell')
        sell_asset_result = AssetManager.get_asset_in_container_list(sell_container_list)
        for asset in sell_asset_result:
            if asset.type_id not in asset_dict:
                asset_dict[asset.type_id] = asset.quantity
            else:
                asset_dict[asset.type_id] += asset.quantity
        for index, data in enumerate(t2mk_data):
            t2mk_data[index].insert(3, asset_dict.get(data[0], 0))
        spreadsheet = FeiShuKahuna.create_user_plan_spreadsheet(user_qq, plan_name)
        t2_cost_sheet = FeiShuKahuna.get_t2_ship_market_sheet(spreadsheet)
        FeiShuKahuna.output_mk_sheet(t2_cost_sheet, t2mk_data)

        res_str =  (f"执行完成, 当前计划条件T2常规市场分析:{t2_cost_sheet.url}\n\n"
                    f"推荐制造：\n")
        for index, data in enumerate(t2mk_data[:10]):
            res_str += (f'{index+1}.{data[1]}\n'
                        f'  利润率:{data[5]:.2%}\n'
                        f'  月利润:{data[6]:,.2f}\n'
                        f'  月销量:{data[12]:,}\n')

        return event.plain_result(res_str)

    @staticmethod
    async def rp_battalship_mk(event: AstrMessageEvent, plan_name: str):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        if plan_name not in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")

        with ThreadPoolExecutor(max_workers=1) as executor:
            battleship_list = SdeUtils.get_battleship()
            battalship_ship_id_list = [SdeUtils.get_id_by_name(name) for name in battleship_list]
            await MarketHistory.refresh_vale_market_history(battalship_ship_id_list)
            future = executor.submit(IndustryAdvice.advice_report, user, plan_name, battleship_list)
            while not future.done():
                await asyncio.sleep(1)
            battalship_mk_data = future.result()

        for data in battalship_mk_data:
            if data[-1] == 'Faction':
                if 'Navy' in data[1] or 'Fleet' in data[1]:
                    more_cost = 100000000
                else:
                    more_cost = 200000000
                data[6] += more_cost
                data[3] -= more_cost
                data[4] = data[3] / data[6]
                data[5] = data[10] * data[4]

        spreadsheet = FeiShuKahuna.create_user_plan_spreadsheet(user_qq, plan_name)
        battalship_mk_sheet = FeiShuKahuna.get_battleship_market_sheet(spreadsheet)
        FeiShuKahuna.output_mk_sheet(battalship_mk_sheet, battalship_mk_data)

        res_str = (f"执行完成, 当前计划条件战列市场分析:{battalship_mk_sheet.url}\n\n"
                   f"推荐制造：\n")
        for index, data in enumerate(battalship_mk_data[:10]):
            res_str += (f'{index + 1}.{data[1]}\n'
                        f'  利润率:{data[4]:.2%}\n'
                        f'  月利润:{data[5]:,.2f}\n'
                        f'  月销量:{data[11]:,}\n')

        return event.plain_result(res_str)

    @staticmethod
    async def rp_capcost(event: AstrMessageEvent, plan_name: str):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        if plan_name not in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")

        with ThreadPoolExecutor(max_workers=1) as executor:
            ship_list = SdeUtils.get_capital_ship()
            plan = [[ship, 1] for ship in ship_list]
            future = executor.submit(IndustryAnalyser.get_cost_data, user, plan_name, plan)
            while not future.done():
                await asyncio.sleep(1)
            cost_data = future.result()

        spreadsheet = FeiShuKahuna.create_user_plan_spreadsheet(user_qq, plan_name)
        cost_sheet = FeiShuKahuna.get_cap_cost_sheet(spreadsheet)
        FeiShuKahuna.output_cost_sheet(cost_sheet, cost_data)

        return event.plain_result(f"执行完成, 当前计划条件旗舰成本:{cost_sheet.url}")

    @staticmethod
    async def rp_costdetail(event: AstrMessageEvent, plan_name: str, product: str, public= False):
        if await try_acquire_lock(calculate_lock, 1):
            try:
                if public:
                    user_qq = int(config['APP']['COST_PLAN_USER'])
                    plan_name = config['APP']['COST_PLAN_NAME']
                    product = ' '.join(event.get_message_str().split(" ")[1:])
                else:
                    user_qq = get_user(event)
                    product = ' '.join(event.get_message_str().split(" ")[4:])

                user = UserManager.get_user(user_qq)
                if plan_name not in user.user_data.plan:
                    raise KahunaException(f"plan {plan_name} not exist")

                if (type_id := SdeUtils.get_id_by_name(product)) is None:
                    return print_name_fuzz_list(event, product)

                detail_dict = IndustryAnalyser.get_cost_detail(user, plan_name, product)
                detail_dict.update({'name': SdeUtils.get_name_by_id(type_id), 'cn_name': SdeUtils.get_cn_name_by_id(type_id)})
                spreadsheet = FeiShuKahuna.create_user_plan_spreadsheet(user_qq, plan_name)
                cost_sheet = FeiShuKahuna.get_detail_cost_sheet(spreadsheet)
                FeiShuKahuna.output_cost_detail_sheet(cost_sheet, detail_dict)

                detail_dict["type_id"] = type_id
                detail_dict["market_detail"] = PriceService.get_price_rouge(product, 'jita')

                pic_path = await PriceResRender.render_single_cost_pic(detail_dict)

                chain = [
                    Image.fromFileSystem(pic_path),
                    Plain(f"详情报表:{cost_sheet.url}")
                ]
                return event.chain_result(chain)
            finally:
                calculate_lock.release()
        else:
            return event.plain_result("已有成本计算进行中，请稍候再试。")

    @staticmethod
    async def rp_sell_list(event: AstrMessageEvent, price_type: str, corp: bool = False):
        if not corp:
            user_qq = get_user(event)
        else:
            user_qq = int(config['APP']['CORP_ASSET_USER'])

        sell_container_list = AssetContainer.get_contain_id_by_qq_tag(user_qq, 'sell')
        sell_asset_result = AssetManager.get_asset_in_container_list(sell_container_list)
        sell_asset_list = list(sell_asset_result)

        sell_asset_list2 = [
            asset for asset in sell_asset_list if
            asset.location_flag == 'CorpSAG4' and SdeUtils.get_category_by_id(asset.type_id) == 'Ship'
        ]

        pic_path = await PriceResRender.render_sell_list(sell_asset_list2, price_type)

        chain = [
            Image.fromFileSystem(pic_path)
        ]
        return event.chain_result(chain)

    @staticmethod
    def refjobs(event: AstrMessageEvent):
        IndustryManager.refresh_running_status()

        return event.plain_result("执行完成")

    @staticmethod
    async def rp_mineral_analyse(
            event: AstrMessageEvent, plan_name: str,
            material_flag: str = 'buy',
            compress_flag: str = 'buy'
    ):
        user_qq = get_user(event)
        user = UserManager.get_user(user_qq)
        if plan_name not in user.user_data.plan:
            raise KahunaException(f"plan {plan_name} not exist")
        if material_flag not in {'buy', 'sell'}:
            return event.plain_result("material_flag must be in {buy, sell}")
        if compress_flag not in {'buy', 'sell'}:
            return event.plain_result("compress_flag must be in {buy, sell}")

        plan_cache = get_user_tmp_cache_prefix(user_qq) + f'{plan_name}_' + 'plan_report.json'
        with open(os.path.join(TMP_PATH, plan_cache), 'r') as file:
            plan_data = json.load(file)
        report_time = datetime.fromisoformat(plan_data['date'])
        report = plan_data['data']

        # 化矿分析
        minedata = report['material']['矿石']
        material_list = [[data[0], data[3]] for data in minedata]

        ref_res = await IndustryAdvice.material_ref_advice(material_list, material_flag, compress_flag)
        need_d = ref_res['need']
        output_str = '采购清单：\n'
        for tid, data in need_d.items():
            output_str += f"{data['name']}\t{data['need']}\n"

        pic_path = await PriceResRender.render_refine_result(ref_res)
        chain = [
            Image.fromFileSystem(pic_path),
            Plain(output_str)
        ]
        return event.chain_result(chain)


class MarketEvent:
    @staticmethod
    async def market_reforder(event: AstrMessageEvent):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(MarketManager.refresh_market)

            while not future.done():
                await asyncio.sleep(1)

            res_log = future.result()
            return event.plain_result(res_log)

    @staticmethod
    async def market_set_ac(event: AstrMessageEvent):
        character_name = ' '.join(event.get_message_str().split(" ")[2:])
        character = CharacterManager.get_character_by_name_qq(character_name, int(event.get_sender_id()))
        MarketManager.set_ac_character(character.character_id)
        return event.plain_result(f"设置市场访问角色为 {character_name}")

    @staticmethod
    async def market_reinit(event: AstrMessageEvent):
        MarketManager.init_market()
        return event.plain_result("初始化市场完成。")

class SdeEvent():
    @staticmethod
    def type(event: AstrMessageEvent, ):
        message_str = event.get_message_str()
        type_name = " ".join(message_str.split(" ")[2:])

        type_id = SdeUtils.get_id_by_name(type_name)
        if type_id:
            market_tree_str = '\n  ↓\n'.join(SdeUtils.get_market_group_list(type_id))
            print_str = (f"enname: {SdeUtils.get_name_by_id(type_id)}\n"
                         f"zhname: {SdeUtils.get_cn_name_by_id(type_id)}\n"
                         f"type_id: {type_id}\n"
                         f"group: {SdeUtils.get_groupname_by_id(type_id)}\n"
                         f"category: {SdeUtils.get_category_by_id(type_id)}\n"
                         f"meta: {SdeUtils.get_metaname_by_typeid(type_id)}\n"
                         f"market_tree: \n{market_tree_str}\n")
            return event.plain_result(print_str)
        else:
            fuzz_list = SdeUtils.fuzz_type(type_name)
            if fuzz_list:
                fuzz_rely = (f"物品 {type_name} 不存在于数据库\n"
                             f"你是否在寻找：\n")
                fuzz_rely += '\n'.join(fuzz_list)
                return event.plain_result(fuzz_rely)

    @staticmethod
    def findtype(event: AstrMessageEvent, ):
        message_str = event.get_message_str()
        type_name = " ".join(message_str.split(" ")[2:])
        fuzz_list = SdeUtils.fuzz_type(type_name, list_len=10)
        if fuzz_list:
            fuzz_rely = (f"你是否在寻找：\n")
            fuzz_rely += '\n'.join(fuzz_list)
            return event.plain_result(fuzz_rely)

    @staticmethod
    def type_id(event: AstrMessageEvent, type_id: int):
        name = SdeUtils.get_name_by_id(type_id)
        if name:
            market_tree_str = '\n  ↓\n'.join(SdeUtils.get_market_group_list(type_id))
            print_str = (f"enname: {SdeUtils.get_name_by_id(type_id)}\n"
                         f"zhname: {SdeUtils.get_cn_name_by_id(type_id)}\n"
                         f"type_id: {type_id}\n"
                         f"group: {SdeUtils.get_groupname_by_id(type_id)}\n"
                         f"category: {SdeUtils.get_category_by_id(type_id)}\n"
                         f"meta: {SdeUtils.get_metaname_by_typeid(type_id)}\n"
                         f"market_tree: \n{market_tree_str}\n")
            return event.plain_result(print_str)
        else:
            return event.plain_result('id不存在于数据库')
