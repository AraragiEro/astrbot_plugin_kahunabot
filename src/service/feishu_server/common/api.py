
import requests
import aiohttp
from cachetools import TTLCache, cached

# kahuna logger
from ...log_server import logger

def post_request(url, **kwargs):
    response = requests.post(url, **kwargs)
    if response.status_code == 200:
        data = response.json()
        return data  # 注意：实际的键可能不同，请参考 ESI 文档
    else:
        logger.error(response.text)
        return None

def get_request(url, **kwargs):
    response = requests.get(url, **kwargs)
    if response.status_code == 200:
        data = response.json()
        return data  # 注意：实际的键可能不同，请参考 ESI 文档
    else:
        logger.error(response.text)
        return None

async def get_request_async(url, log=True, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, **kwargs) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                response_text = await response.text()
                if log:
                    logger.warning(response_text)
                return None

def patch_request(url, **kwargs):
    response = requests.patch(url, **kwargs)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        logger.error(response.text)
        return None

def put_request(url, **kwargs):
    response = requests.put(url, **kwargs)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        logger.error(response.text)
        return None

def post_tenant_access_token(app_id, secret):
    url = f'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    params = {
        "app_id": app_id,
        "app_secret": secret
    }
    return post_request(url, params=params)

def post_sheet_value(access_token: str, sheet_token: str, data: dict()) -> dict:
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{sheet_token}/values'
    headers = {"Authorization": f"Bearer {access_token}"}
    return post_request(url, headers=headers, json=data)

def get_sheets_v3_sheets_query(access_token: str, sheet_token: str) -> dict:
    url = f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{sheet_token}/sheets/query'
    headers = {"Authorization": f"Bearer {access_token}"}

    return get_request(url, headers=headers)

def get_sheets_v3_spreadsheets(access_token: str, spreadsheet_token: str) -> dict:
    url = f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}'
    headers = {"Authorization": f"Bearer {access_token}"}
    return get_request(url, headers=headers)

def post_sheets_v3_spreadsheets(access_token: str, title: str, folder_token) -> dict:
    url = f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets'
    headers = {"Authorization": f"Bearer {access_token}"}
    json = {
        'title': title,
        'folder_token': folder_token
    }
    return post_request(url, headers=headers, json=json)

def get_drive_v1_files(access_token: str, folder_token: str) -> dict:
    url = f'https://open.feishu.cn/open-apis/drive/v1/files'
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "page_size": 200,
        'folder_token': folder_token
    }
    return get_request(url, headers=headers, params=params)

def patch_sheets_v3_spreadsheets(access_token: str, spreadsheet_token: str, title: str) -> dict:
    url = f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}'
    headers = {"Authorization": f"Bearer {access_token}"}
    json = {
        'title': title
    }
    return patch_request(url, headers=headers, json=json)

def patch_drive_v2_permissions_public(access_token: str, file_token: str, type: str, data: dict) -> dict:
    url = f'https://open.feishu.cn/open-apis/drive/v2/permissions/{file_token}/public'
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {'type':type}
    data = data
    patch_request(url, headers=headers, params=params, json=data)

def get_drive_v2_permissions_token_public(access_token: str, file_token: str, type: str) -> dict:
    url = f'https://open.feishu.cn/open-apis/drive/v2/permissions/{file_token}/public'
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {'type':type}
    return get_request(url, headers=headers, params=params)

def post_sheets_v2_spreadsheets_values_batch_update(access_token: str, sheet_token: str, data: dict) -> dict:
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{sheet_token}/values_batch_update'
    headers = {"Authorization": f"Bearer {access_token}"}
    json = data
    return post_request(url, headers=headers, json=json)

def put_sheets_v2_spreadsheets_values(access_token: str, sheet_token: str, data: dict) -> dict:
    """ 单个范围写入数据 """
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{sheet_token}/values'
    headers = {"Authorization": f"Bearer {access_token}"}
    json = data
    return put_request(url, headers=headers, json=json)

def get_sheets_v3_spreadsheets_spreadsheet_token_sheets_sheet_id(
        access_token: str,
        spreadsheet_token: str,
        sheet_id: str
):
    """ 查询工作表 """
    url = f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/{sheet_id}'
    headers = {"Authorization": f"Bearer {access_token}"}
    return get_request(url, headers=headers)

def post_sheets_v2_spreadsheets_spreadsheet_token_sheets_batch_update(
        access_token: str,
        spreadsheet_token: str,
        data: dict
):
    """ 操作工作表【增删改复制】 """
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/sheets_batch_update'
    headers = {"Authorization": f"Bearer {access_token}"}
    json = data

    return post_request(url, headers=headers, json=json)

# https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/:spreadsheetToken/style
def put_sheets_v2_spreadsheets_spreadsheetToken_style(
        access_token: str,
        spreadsheet_token: str,
        data: dict
):
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/style'
    headers = {"Authorization": f"Bearer {access_token}"}
    json = data
    return put_request(url, headers=headers, json=json)

# https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/:spreadsheetToken/dimension_range
def put_sheets_v2_spreadsheets_spreadsheetToken_dimension_range(
        access_token: str,
        spreadsheet_token: str,
        data: dict
):
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/dimension_range'
    headers = {"Authorization": f"Bearer {access_token}"}
    json = data
    return put_request(url, headers=headers, json=json)

# https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/:spreadsheet_token/condition_formats/batch_create
def post_sheets_v2_spreadsheets_spreadsheetToken_condition_formats_batch_create(
        access_token: str,
        spreadsheet_token: str,
        data: dict
):
    url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/condition_formats/batch_create'
    headers = {"Authorization": f"Bearer {access_token}"}
    json = data
    return post_request(url, headers=headers, json=json)

# https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/:spreadsheet_token/sheets/:sheet_id
def get_sheets_v3_spreadsheets_spreadsheetToken_sheets_sheetId(
        access_token: str,
        spreadsheet_token: str,
        sheet_id: str
):
    url = f'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/{sheet_id}'
    headers = {"Authorization": f"Bearer {access_token}"}
    return get_request(url, headers=headers)