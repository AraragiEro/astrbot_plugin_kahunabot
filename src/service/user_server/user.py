from pydantic import BaseModel
from datetime import datetime, timedelta
import json
from functools import lru_cache

from ..database_server.model import User as M_User, UserData as M_UserData
from ..character_server.character_manager import CharacterManager
from ...utils import KahunaException
from ..feishu_server.feishu_kahuna import FeiShuKahuna


class UserData():
    user_qq: int = 0
    user_data_colunms = ["plan", "alias", "sell_data"]
    """ 
    plan: dict = {
        plan_name: {
            bp_matcher: Matcher,
            st_matcher: Matcher,
            prod_block_matcher: Matcher,
            plan: [[type_id: quantity], ...]
        }, ...
    }
    alias: dict = {
        character_id: character_name, ...
    }
    """
    plan: list = []
    alias: dict = dict()

    def __init__(self, user_qq: int):
        self.user_qq = user_qq
        plan: list = []
        alias: dict = {}

        """ sell setting """
        sell_data: dict = {
            "name": "",
            "sell_container_id": 0,
            "sell_location_flag": None,
            "market_group": [],
            "group": [],
            "meta": [],
            "category": []
        }

        self.load_self_data()

    def get_from_db(self) -> M_UserData:
        return M_UserData.get_or_none(M_UserData.user_qq == self.user_qq)

    def insert_to_db(self) -> None:
        obj = M_UserData.get_or_none(M_UserData.user_qq == self.user_qq)
        if not obj:
            obj = M_UserData()

        obj.user_qq = self.user_qq
        obj.user_data = self.dums_self_data()

        obj.save()

    def dums_self_data(self) -> str:
        data = {
            key: getattr(self, key) for key in self.user_data_colunms
        }

        return json.dumps(data, indent=4)

    def load_self_data(self) -> None:
        data = self.get_from_db()
        if not data:
            data_dict = {}
        else:
            data_dict = json.loads(data.user_data)
        for key in self.user_data_colunms:
            setattr(self, key, data_dict.get(key, dict()))

    def get_plan_detail(self, plan_name: str) -> str:
        if plan_name not in self.plan:
            raise KahunaException("plan not found.")
        plan_dict = self.plan[plan_name]


        res_str = (f"bp_matcher: {plan_dict['bp_matcher']}\n"
                   f"st_matcher: {plan_dict['st_matcher']}\n"
                   f"prod_block_matcher: {plan_dict['prod_block_matcher']}\n"
                   f"plan:\n")
        plan_str = "\n".join([f"{index + 1}.{plan[0]}: {plan[1]}" for index, plan in enumerate(plan_dict["plan"])])

        return res_str + "\n" + plan_str

    @property
    def feishu_token(self):
        if not self.feishu_sheet_token:
            raise KahunaException("create sheet first.")
        return self.feishu_sheet_token

    @feishu_token.setter
    def feishu_token(self, token: str):
        self.feishu_sheet_token = token

class User():
    user_qq: int
    create_date: datetime
    expire_date: datetime
    main_character_id: int = 0
    plan_max: int = 5
    user_data: UserData = None

    def __init__(self, qq: int, create_date: datetime, expire_date: datetime):
        self.user_qq = qq
        self.create_date = create_date
        self.expire_date = expire_date

        self.user_data = UserData(qq)
        self.user_data.load_self_data()

    def get_from_db(self):
        return M_User.get_or_none(M_User.user_qq == self.user_qq)

    def init_time(self):
        self.create_date = datetime.now()
        self.expire_date = datetime.now()

    def insert_to_db(self):
        user_obj = M_User.get_or_none(M_User.user_qq == self.user_qq)
        if not user_obj:
            user_obj = M_User()

        user_obj.user_qq = self.user_qq
        user_obj.create_date = self.create_date
        user_obj.expire_date = self.expire_date
        user_obj.main_character_id = self.main_character_id

        user_obj.save()
        self.user_data.insert_to_db()

    @property
    def info(self):
        res = (f"用户:{self.user_qq}\n"
                f"创建时间:{self.create_date}\n"
                f"到期时间:{self.expire_date}\n"
                f"剩余时间:{max(timedelta(), self.expire_date - datetime.now())}\n")
                # f"主角色：{CharacterManager.get_character_by_id(self.main_character_id).character_name}\n")
        if self.main_character_id != 0:
            res += f"主角色：{CharacterManager.get_character_by_id(self.main_character_id).character_name}\n"
        return res

    @property
    def member_status(self):
        return self.expire_date > datetime.now()

    def add_member_time(self, day: int):
        add_time = timedelta(days=day)

        self.expire_date = max(self.expire_date, datetime.now()) + add_time
        self.insert_to_db()
        return self.expire_date

    def clean_member_time(self):
        self.expire_date = datetime.now()
        self.insert_to_db()

    def delete(self):
        user_obj = M_User.get_or_none(self.user_qq)
        if not user_obj:
            return

        user_obj.delete().execute()

    def set_plan_product(self, plan_name: str, product: str, quantity: int):
        if plan_name not in self.user_data.plan:
            raise KahunaException(
                "计划不存在，请使用 .Inds plan create [plan_name] [bp_matcher] [st_matcher] [prod_block_matcher] 创建")
        self.user_data.plan[plan_name]["plan"].append([product, quantity])
        self.user_data.insert_to_db()

    def create_plan(self, plan_name: str,
                    bp_matcher, st_matcher, prod_block_matcher
                    ):
        if len(self.user_data.plan) - 3 >= self.plan_max:
            raise KahunaException(f"you can only create {self.plan_max} plans at most.")
        if plan_name not in self.user_data.plan:
            self.user_data.plan[plan_name] = {}

        self.user_data.plan[plan_name]["bp_matcher"] = bp_matcher.matcher_name
        self.user_data.plan[plan_name]["st_matcher"] = st_matcher.matcher_name
        self.user_data.plan[plan_name]["prod_block_matcher"] = prod_block_matcher.matcher_name
        self.user_data.plan[plan_name]["manucycletime"] = 24 # hour
        self.user_data.plan[plan_name]['reaccycletime'] = 24
        self.user_data.plan[plan_name]['container_block'] = []
        self.user_data.plan[plan_name]["plan"] = []
        self.user_data.insert_to_db()

    def delete_plan_prod(self, plan_name: str, index: int):
        if plan_name not in self.user_data.plan:
            raise KahunaException("plan not found.")
        if 0 <= index < len(self.user_data.plan[plan_name]["plan"]):
            self.user_data.plan[plan_name]["plan"].pop(index)
        self.user_data.insert_to_db()

    def set_manu_cycle_time(self, plan_name: str, cycle_time: int):
        if plan_name not in self.user_data.plan:
            raise KahunaException("plan not found.")
        self.user_data.plan[plan_name]["manucycletime"] = cycle_time
        self.user_data.insert_to_db()

    def set_reac_cycle_time(self, plan_name: str, cycle_time: int):
        if plan_name not in self.user_data.plan:
            raise KahunaException("plan not found.")
        self.user_data.plan[plan_name]["reaccycletime"] = cycle_time
        self.user_data.insert_to_db()

    def set_reac_line_num(self, plan_name: str, line_num: int):
        if plan_name not in self.user_data.plan:
            raise KahunaException("plan not found.")
        self.user_data.plan[plan_name]["reaclinenum"] = line_num
        self.user_data.insert_to_db()

    def set_manu_line_num(self, plan_name: str, line_num: int):
        if plan_name not in self.user_data.plan:
            raise KahunaException("plan not found.")
        self.user_data.plan[plan_name]["manulinenum"] = line_num
        self.user_data.insert_to_db()

    def delete_plan(self, plan_name: str):
        if plan_name not in self.user_data.plan:
            raise KahunaException("plan not found.")
        self.user_data.plan.pop(plan_name)
        self.insert_to_db()

    def add_alias_character(self, character_id_list):
        for character_data in character_id_list:
            if character_data[0] not in self.user_data.alias:
                self.user_data.alias[character_data[0]] = character_data[1]
        self.user_data.insert_to_db()

    def add_container_block(self, plan_name: str, container_id: int):
        if plan_name not in self.user_data.plan:
            raise KahunaException("plan not found.")
        if "container_block" not in self.user_data.plan[plan_name]:
            self.user_data.plan[plan_name]["container_block"] = []
        if container_id not in self.user_data.plan[plan_name]["container_block"]:
            self.user_data.plan[plan_name]["container_block"].append(container_id)
        self.user_data.insert_to_db()

    def del_container_block(self, plan_name: str, container_id: int):
        if plan_name not in self.user_data.plan:
            raise KahunaException("plan not found.")
        if "container_block" not in self.user_data.plan[plan_name]:
            self.user_data.plan[plan_name]["container_block"] = []
        if container_id in self.user_data.plan[plan_name]["container_block"]:
            self.user_data.plan[plan_name]["container_block"].remove(container_id)
        self.user_data.insert_to_db()


