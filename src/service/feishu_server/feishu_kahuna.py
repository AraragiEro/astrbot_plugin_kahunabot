from functools import lru_cache
from .client import FeiShuClient
from ..config_server.config import config
from .client import LinkShareEntity
from .common.spreadsheets import Spreadsheets, Sheet
from .common.spreadsheets import ANYONE_READABLE
from .common.client_utils import format_work_tree, format_material_tree, format_work_flow
from ..sde_service import SdeUtils

fs_client = FeiShuClient(config['FEISHU']['APP_ID'], config['FEISHU']['SECRET_ID'])

class FeiShuKahuna:
    client: FeiShuClient = None

    @classmethod
    def set_client(cls, client: FeiShuClient):
        cls.client = client

    @classmethod
    def set_folder_token(cls, folder_token: str):
        cls.client.set_folder_token(folder_token)

    @classmethod
    def get_user_plan_sheet_name(self, user_qq: int, plan_name):
        return f"kahunaBot_{user_qq}_{plan_name}_data"

    @classmethod
    def create_user_plan_spreadsheet(cls, user_qq: int, plan_name: str) -> Spreadsheets:
        sheet_name = cls.get_user_plan_sheet_name(user_qq, plan_name)
        return cls.client.create_spreadsheets(sheet_name)

    @classmethod
    def get_user_plan_spreadsheet(cls, user_qq: int, plan_name) -> Spreadsheets:
        user_sheet_name = cls.get_user_plan_sheet_name(user_qq, plan_name)
        return cls.client.get_spreadsheets(user_sheet_name)

    """ == 默认表配置 == """
    @classmethod
    def get_worktree_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet("流程树")

    @classmethod
    def get_workflow_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet("工作流")

    @classmethod
    def get_material_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet("材料单")

    @classmethod
    def get_logistic_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet('物流清单')

    @classmethod
    def get_t2_cost_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet("T2船成本")

    @classmethod
    def get_cap_cost_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet("旗舰成本")

    @classmethod
    def get_t2_ship_market_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet('T2常规市场')

    @classmethod
    def get_battleship_market_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet('战列市场')

    @classmethod
    def get_detail_cost_sheet(cls, spreadsheet: Spreadsheets) -> Sheet:
        return spreadsheet.create_sheet('单品分析')

    """ == 默认表方法 == """
    @classmethod
    def create_default_spreadsheet(cls, spreadsheet: Spreadsheets) -> Spreadsheets:
        work_tree_sheet = cls.get_worktree_sheet(spreadsheet)
        workflow_sheet = cls.get_workflow_sheet(spreadsheet)
        material_sheet = cls.get_material_sheet(spreadsheet)

        spreadsheet.permission.link_share_entity = ANYONE_READABLE

    """== 写入数据方法 =="""
    @classmethod
    def output_work_tree(cls, sheet: Sheet, data: dict):
        sheet.clear_sheet()
        data = format_work_tree(data)
        sheet.set_value([1, 1], data)

    @classmethod
    def output_material_tree(cls, sheet: Sheet, data: dict):
        sheet.clear_sheet()
        data = format_material_tree(data)
        sheet.set_value([1, 1], data)

        sheet.set_dimension(1, 1, dimension_type='COLUMNS', visible=True, fixed_size=45)
        sheet.set_dimension(2, 3, dimension_type='COLUMNS', visible=True, fixed_size=140)
        sheet.set_dimension(4, 7, dimension_type='COLUMNS', visible=True, fixed_size=95)
        sheet.set_dimension(8, 9, dimension_type='COLUMNS', visible=True, fixed_size=85)
        sheet.set_dimension(10, 11, dimension_type='COLUMNS', visible=True, fixed_size=120)
        sheet.set_dimension(12, 13, dimension_type='COLUMNS', visible=True, fixed_size=60)

        sheet.set_format([8, 1], [4, len(data)], {'formatter': '#,##0.00'})
        sheet.set_format([4, 1], [4, len(data)], {'formatter': '#,##0'})

    @classmethod
    def output_work_flow(cls, sheet: Sheet, data: dict):
        sheet.clear_sheet()

        manu_flow, reac_flow = format_work_flow(data)

        sheet.set_value([1, 1], reac_flow)
        sheet.set_value([5, 1], manu_flow)

        reac_lines_cost = sum([data[2] for data in reac_flow[1:]])
        manu_lines_cost = sum([data[2] for data in manu_flow[1:]])
        detail_data = [
            ['反应线消耗总计', reac_lines_cost],
            ['制造线消耗总计', manu_lines_cost],
        ]
        sheet.set_value([9, 1], detail_data)

        format_data = {
            'font': {
                'bold': True,
                'fontSize': '12pt/1.5'
            }
        }
        sheet.set_format([1, 1], [len(reac_flow[0]), len(reac_flow)], format_data)
        sheet.set_format([5, 1], [len(manu_flow[0]), len(manu_flow)], format_data)

        sheet.set_dimension(1, 1, dimension_type='COLUMNS', visible=True, fixed_size=300)
        sheet.set_dimension(5, 1, dimension_type='COLUMNS', visible=True, fixed_size=300)

    @classmethod
    def output_logistic_plan(cls, sheet, logistic_dict: dict):
        '''将物流清单输出到飞书表格'''
        sheet.clear_sheet()

        transport_data = logistic_dict['transport']

        transport_list_head = ['提供', '需求', '物品', '数量', '体积']
        transport_list = [[key[0], key[1], SdeUtils.get_name_by_id(key[2]), value,
                           SdeUtils.get_invtype_packagedvolume_by_id(key[2]) * value]
                          for key, value in transport_data.items()]
        transport_list.sort(key=lambda x: x[0], reverse=True)
        transport_list = [transport_list_head] + transport_list
        sheet.set_value([1, 1], transport_list)

    @classmethod
    def output_cost_sheet(cls, sheet: Sheet, data: dict):
        sheet.clear_sheet()
        data = [[k] + v for k, v in data.items()]
        data = [['name', 'material_cost', 'eff_cost', 'total']] + data

        format_data = {
            'formatter': '#,##0.00'
        }

        sheet.set_value([1, 1], data)
        format_data = {
            'formatter': '#,##0.00'
        }
        sheet.set_format([2, 1], [len(data[0]) - 1, len(data)], format_data)
        sheet.set_dimension(2, 4, dimension_type='COLUMNS', visible=True, fixed_size=130)

        format_data = {
            'font': {
                'bold': True,
                'fontSize': '12pt/1.5'
            }
        }
        sheet.set_format([1, 1], [1, len(data)], format_data)

    @classmethod
    def output_mk_sheet(cls, sheet: Sheet, data: list):
        data = [['id', 'name', 'cn_name', '利润', '利润率', '月利润空间', '成本', '4h出单', '吉他收单', '吉他出单',
                 '月流水', '月销量', 'meta']] + data
        sheet.set_value([1, 1], data)

        sheet.set_format([4,1], [1, len(data)], {'formatter': '#,##0.00'})
        sheet.set_format([5, 1], [1, len(data)], {'formatter': '0.00%'})
        sheet.set_format([6, 1], [7, len(data)], {'formatter': '#,##0.00'})

    @classmethod
    def output_cost_detail_sheet(cls, sheet: Sheet, detail_dict: dict):
        '''输出单品材料解析到飞书表格'''
        sheet.clear_sheet()

        # 输出原料type细分
        material_dict = detail_dict['material']
        eiv_data = detail_dict['eiv']
        type_cost_detail = ['总成本', detail_dict['total_cost']]
        type_cost_head = ['id', detail_dict['name'], detail_dict['cn_name'], '成本', '占比']
        type_cost_list = [[tid, SdeUtils.get_name_by_id(tid), SdeUtils.get_cn_name_by_id(tid)] + data
                          for tid, data in material_dict.items()]
        type_cost_list += [['', 'eiv_cost', '系数', eiv_data[0], eiv_data[1]]]
        type_cost_list.sort(key=lambda x: x[3], reverse=True)
        type_cost_list = [type_cost_head] + type_cost_list

        sheet.set_value([1, 1], type_cost_list)
        sheet.set_format([4, 1], [1, len(type_cost_list)], {'formatter': '#,##0.00'})
        sheet.set_format([5, 1], [1, len(type_cost_list)], {'formatter': '0.00%'})

        # 输出原料group细分
        group_detail = detail_dict['group_detail']
        group_header = ['组分类', '成本', '占比']
        group_cost_list = [[group, data[0], data[1]] for group, data in group_detail.items()]
        group_cost_list.sort(key=lambda x: x[1], reverse=True)
        group_cost_list = [group_header] + group_cost_list

        sheet.set_value([7, 1], group_cost_list)
        sheet.set_format([8, 1], [1, len(group_cost_list)], {'formatter': '#,##0.00'})
        sheet.set_format([9, 1], [1, len(group_cost_list)], {'formatter': '0.00%'})


FeiShuKahuna.set_client(fs_client)
FeiShuKahuna.set_folder_token(config['FEISHU']['FOLDER_ROOT'])