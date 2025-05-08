from cachetools import TTLCache, cached

from . import api

cache = TTLCache(maxsize=50, ttl=10)

class FeishuException(Exception):
    def __init__(self, message):
        super(FeishuException, self).__init__(message)
        self.message = message

def excol(n: int) -> str:
    """Convert an integer to the corresponding Excel column label."""
    if n < 1:
        raise ValueError(f"{type(n)}: Input must be a positive integer.")

    column_label = ""
    while n > 0:
        n -= 1
        column_label = chr(n % 26 + 65) + column_label
        n //= 26

    return column_label

@cached(cache)
def get_spreadsheet_token_by_name(access_token: str, folder_token, spreadsheet_name: str) -> str:
    """Get the spreadsheet token by spreadsheet name."""
    # get drive file
    drive_res = api.get_drive_v1_files(access_token, folder_token)
    filelist = drive_res['data']['files']

    for file in filelist:
        if file['name'] == spreadsheet_name:
            return file['token']

@cached(cache)
def get_sheet_id_by_name(access_token: str, sheet_token: str, sheet_name: str):
    spsheet_query_res = api.get_sheets_v3_sheets_query(access_token, sheet_token)
    sheets_list = spsheet_query_res['data']['sheets']

    for sheet in sheets_list:
        if sheet['title'] == sheet_name:
            return sheet['sheet_id']
    return None

def create_sheet_request_data(title: str):
    return {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": title,
                        "index": 1
                    }
                }
            }
        ]
    }

def delete_sheet_request_data(sheet_id: str):
    return {
        "requests": [
            {
                "deleteSheet": {
                    "sheetId": sheet_id
                }
            }
        ]
    }

def format_work_tree(datadict: dict):
    head = [[
        'M/R',
        'id',
        'name',
        '名称',
        '库存',
        '缺失',
        '总计',
        '运行中',
        '剩余流程',
        '总流程',
        '蓝图数量',
        '蓝图流程',
        '状态']]
    output = []
    key = list(datadict.keys())
    key.sort(reverse=True)
    key = key[:-1]
    for k in key:
        data = datadict[k]
        data = head + data
        output = output + data + [["" for _ in range(len(head[0]))]]

    return output


def format_material_tree(datadict: dict):
    """Format material tree data into a structured output for spreadsheets."""

    # Generate header
    header = [
        'tid',
        'name',
        '名称',
        '缺失',
        '冗余',
        '总需求',
        '库存',
        'jita收单',
        'jita出单',
        '收单价格',
        '扫单差',
        '已挂单',
        '已收到',
        '计划详情'
    ]

    # Prepare data list
    output = []
    output_list = ['矿石', '冰矿产物', '燃料块', '元素', '气云', '行星工业', '杂货', '反应物']

    for key in output_list:
        datadict[key].sort(key=lambda x: (x[3], x[0]))
        output += [[key] + ['' for i in range(len(header) - 1)]] + [header] + datadict[key] + [["" for _ in range(len(header))]]


    return output

def format_work_flow(datadict: dict):
    """Format work flow data into a structured output for spreadsheets."""

    reac_header = [['反应序列', '流程', '产线']]
    manu_header = [['制造序列', '流程', '产线']]

    return manu_header + datadict['manu_flow'], reac_header + datadict['reac_flow']