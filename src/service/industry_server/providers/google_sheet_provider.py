# providers/google_sheets_provider.py
from typing import List, Tuple, Dict, Any
import os
import aiohttp
import asyncio
import urllib.parse
import pandas as pd
import io

from ..third_provider import Provider
from ...sde_service import SdeUtils
# from ...database_server.utils import RefreshDateUtils
from ...database_server.sqlalchemy.kahuna_database_utils import (
    RefreshDataDBUtils
)

class GoogleSheetsProvider(Provider):
    """
    从Google Sheets获取资产的供货商
    使用aiohttp实现，支持同步和异步操作
    仅支持访问公开表格
    支持从多个工作表中获取数据
    """
    PROVIDER_ID = "google_sheets"
    PROVIDER_NAME = "Google Sheets Provider"

    def __init__(self, provider_id: str = None, name: str = None, config: Dict[str, Any] = None):
        """
        初始化Google Sheets供货商

        参数:
            provider_id: 覆盖默认的provider_id (可选)
            name: 覆盖默认的provider名称 (可选)
            config: 配置参数，必须包含：
                - sheet_id: Google表格ID
                - sheet_name: 工作表名称或名称列表 (可选，默认为["Sheet1"])
                               字符串将自动转换为单元素列表
                - proxy: 代理地址 (可选)
                - id_column: 资产ID列名 (可选，默认为asset_id或id)
                - quantity_column: 数量列名 (可选，默认为quantity或amount)
        """
        # 使用默认ID和名称，除非明确覆盖
        effective_id = provider_id or self.PROVIDER_ID
        effective_name = name or self.PROVIDER_NAME

        # 调用父类初始化
        super().__init__(effective_id, effective_name, config)

        # 验证必要配置
        if not config:
            raise ValueError("Configuration is required")

        self.sheet_id = config.get('sheet_id')
        
        # 处理 sheet_name 参数，确保它是列表类型
        sheet_name = config.get('sheet_name', ['Sheet1'])
        if isinstance(sheet_name, str):
            self.sheet_names = [sheet_name]
        elif isinstance(sheet_name, list):
            self.sheet_names = sheet_name
        else:
            raise ValueError("sheet_name must be a string or a list of strings")
        
        self.proxy = config.get('proxy')
        self.id_column = config.get('id_column', None)  # 将在获取数据时检查多个可能的列名
        self.quantity_column = config.get('quantity_column', None)  # 同上

        if not self.sheet_id:
            raise ValueError("sheet_id is required in config")

        if not self.sheet_names:
            raise ValueError("At least one sheet_name must be provided")

    def get_refreshdate_id(self):
        return f'provider_{self.provider_id}_refreshdate'

    async def initialize(self) -> bool:
        """
        初始化供货商，验证参数并测试连接

        返回:
            bool: 初始化是否成功
        """
        return True
        # try:
        #     # 尝试获取数据，验证连接是否正常
        #     test_data = await self.get_assets()
        #     self.logger.info(f"Successfully connected to Google Sheet, found {len(test_data)} assets from {len(self.sheet_names)} sheets")
        #     return True
        #
        # except Exception as e:
        #     self.logger.error(f"Failed to initialize Google Sheets provider: {e}")
        #     return False

    async def get_assets(self) -> List[Tuple[str, float]]:
        """
        从所有配置的工作表获取资产列表并合并结果 (同步版本)

        返回:
            List[Tuple[str, float]]: 资产列表，每项为(资产ID, 数量)元组
        """
        # 对于同步调用，运行异步函数
        if 'cache' in self.cache and not await RefreshDataDBUtils.out_of_hour_interval(self.get_refreshdate_id(), 2):
            self.logger.info(
                f"Successfully connected to Google Sheet, found {len(self.cache['cache'])} assets from cache of {len(self.sheet_names)} sheets")
            return self.cache['cache']
        res = await self.get_assets_async()
        self.cache['cache'] = res
        self.logger.info(
            f"Successfully connected to Google Sheet, found {len(res)} assets from {len(self.sheet_names)} sheets")
        return res

    async def get_assets_async(self) -> List[Tuple[str, float]]:
        """
        从所有配置的工作表获取资产列表并合并结果 (异步版本)

        返回:
            List[Tuple[str, float]]: 资产列表，每项为(资产ID, 数量)元组
        """
        # 并发获取所有工作表数据
        all_assets_tasks = []
        for sheet_name in self.sheet_names:
            all_assets_tasks.append(self._get_sheet_data_async(sheet_name))
        
        # 等待所有任务完成
        all_sheet_assets = await asyncio.gather(*all_assets_tasks, return_exceptions=True)

        # 合并所有工作表的资产，同时处理可能的异常
        combined_assets = []
        for i, sheet_assets in enumerate(all_sheet_assets):
            sheet_name = self.sheet_names[i]
            if isinstance(sheet_assets, Exception):
                self.logger.error(f"Error fetching sheet '{sheet_name}': {sheet_assets}")
                continue
            
            self.logger.info(f"Retrieved {len(sheet_assets)} assets from sheet '{sheet_name}'")
            combined_assets.extend(sheet_assets)
            
        # 合并相同ID的资产
        assets_dict = {}
        for asset_id, quantity in combined_assets:
            if asset_id in assets_dict:
                assets_dict[asset_id] += quantity
            else:
                assets_dict[asset_id] = quantity
                
        # 转换回元组列表
        merged_assets = [(asset_id, quantity) for asset_id, quantity in assets_dict.items()]
        
        return await self.validate_assets(merged_assets)

    async def validate_assets(self, assets: List[Tuple[str, str]]) -> List[Tuple[int, int]]:
        """
        验证资产列表的格式和内容

        参数:
            assets: 原始资产列表

        返回:
            验证后的资产列表
        """
        result = []
        for asset in assets:
            if not isinstance(asset, tuple) or len(asset) != 2:
                self.logger.warning(f"Invalid asset format: {asset}, expected (id, quantity) tuple")
                continue

            tid, quantity = asset
            if not tid or not quantity:
                continue

            # 确保tid是整形
            if not isinstance(tid, int):
                tid = int(tid)

            # 确保quantity是整形且大于0
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    self.logger.warning(f"Ignoring asset {tid} with non-positive quantity: {quantity}")
                    continue
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid quantity for asset {tid}: {quantity}")
                continue

            result.append((tid, quantity))

        await RefreshDataDBUtils.update_refresh_date(self.get_refreshdate_id())
        return result

    async def _get_sheet_data_async(self, sheet_name: str) -> List[Tuple[str, float]]:
        """
        从指定的工作表异步获取数据
        
        参数:
            sheet_name: 工作表名称
            
        返回:
            List[Tuple[str, float]]: 资产列表，每项为(资产ID, 数量)元组
        """
        try:
            # 设置代理
            proxy = self.proxy if self.proxy else None

            # 对包含空格的工作表名称进行编码
            encoded_sheet_name = urllib.parse.quote(sheet_name)
            url = f'https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}'

            # 使用 aiohttp 异步请求
            async with aiohttp.ClientSession() as session:
                # 创建请求选项
                request_kwargs = {
                    'timeout': aiohttp.ClientTimeout(total=30)
                }
                
                # 添加代理设置
                if proxy:
                    request_kwargs['proxy'] = proxy

                # 发送请求
                async with session.get(url, **request_kwargs) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Error response for sheet '{sheet_name}': {error_text}")
                        raise Exception(f"Error fetching sheet '{sheet_name}': {response.status}")

                    # 读取响应内容
                    content = await response.text()
                    
                    # 检查内容是否为空
                    if not content.strip():
                        self.logger.warning(f"Sheet '{sheet_name}' returned empty content")
                        return []

                    # 使用pandas处理CSV数据
                    df = pd.read_csv(io.StringIO(content))
                    
                    # 检查DataFrame是否为空
                    if df.empty:
                        self.logger.warning(f"Sheet '{sheet_name}' has no data")
                        return []

                    # 将DataFrame转换为字典列表
                    data = df.to_dict('records')

                    # 提取资产ID和数量
                    assets = self._extract_assets_from_data(data, sheet_name)

                    return assets

        except Exception as e:
            self.logger.error(f"Error getting data from sheet '{sheet_name}': {e}")
            raise

    def _extract_assets_from_data(self, data: List[Dict], sheet_name: str = None) -> List[Tuple[str, float]]:
        """
        从数据中提取资产ID和数量

        参数:
            data: 字典列表，表示表格数据
            sheet_name: 工作表名称，用于日志输出

        返回:
            资产列表，每项为(资产ID, 数量)元组
        """
        assets = []
        
        if not data:
            return assets

        # 可能的ID列名称和数量列名称
        id_columns = [self.id_column] if self.id_column else ['asset_id', 'id', 'tid', 'asset', 'item_id', 'item', 'type_id']
        qty_columns = [self.quantity_column] if self.quantity_column else ['quantity', 'amount', 'qty', 'count', 'value']

        # 检测表头中实际存在的列
        detected_id_col = None
        detected_qty_col = None

        if data:
            sample_row = data[0]
            # 检测ID列
            for col in id_columns:
                if col in sample_row:
                    detected_id_col = col
                    break

            # 检测数量列
            for col in qty_columns:
                if col in sample_row:
                    detected_qty_col = col
                    break

        if not detected_id_col or not detected_qty_col:
            sheet_info = f" in sheet '{sheet_name}'" if sheet_name else ""
            column_names = list(data[0].keys()) if data else []
            self.logger.error(f"Could not detect ID or quantity columns{sheet_info}. Available columns: {column_names}")
            raise ValueError(
                f"Could not detect ID or quantity columns{sheet_info}. Please specify id_column and quantity_column in config")

        # 提取资产
        for row in data:
            try:
                asset_id = row.get(detected_id_col)
                quantity = row.get(detected_qty_col)

                if asset_id is not None and quantity is not None:
                    assets.append((str(asset_id), str(quantity)))
            except (ValueError, TypeError) as e:

                self.logger.warning(f"Error processing row{' in sheet '+sheet_name if sheet_name else ''}: {row}, {e}")

        return assets

    def shutdown(self) -> None:
        """
        清理资源
        """
        # 清除代理环境变量
        if self.proxy:
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']

        self.logger.info(f"Google Sheets provider '{self.name}' shut down")
        
    async def shutdown_async(self) -> None:
        """
        异步清理资源
        """
        self.shutdown()  # 当前清理操作不需要异步

class YueseProvider(GoogleSheetsProvider):
    async def validate_assets(self, assets: List[Tuple[str, str]]) -> List[Tuple[int, int]]:
        result = []
        for asset in assets:
            if not isinstance(asset, tuple) or len(asset) != 2:
                self.logger.warning(f"Invalid asset format: {asset}, expected (id, quantity) tuple")
                continue

            name, quantity = asset
            tid = SdeUtils.get_id_by_name(name)
            quantity = int(quantity.replace(',', ''))
            if not tid or not quantity:
                continue
            # 确保tid是整形
            if not isinstance(tid, int):
                tid = int(tid)

            # 确保quantity是整形且大于0
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    self.logger.warning(f"Ignoring asset {tid} with non-positive quantity: {quantity}")
                    continue
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid quantity for asset {tid}: {quantity}")
                continue

            result.append((tid, quantity))

        return result