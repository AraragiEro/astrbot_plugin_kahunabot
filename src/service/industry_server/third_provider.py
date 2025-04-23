# third_provider.py
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional, Type
import logging
import uuid
import os
from cachetools import TTLCache, cached

from ..log_server import logger

# 获取当前脚本文件的完整路径
script_file_path = os.path.abspath(__file__)

# 获取脚本文件所在目录
script_dir = os.path.dirname(script_file_path)

class Provider(ABC):
    """
    第三方供货者对象基类
    所有供货对象必须继承此类并实现必要的方法
    """

    def __init__(self, provider_id: str = None, name: str = None, config: Dict[str, Any] = None):
        """
        初始化供货者对象

        参数:
            provider_id: 供货商唯一ID，如果未提供则自动生成
            name: 供货商名称
            config: 供货商配置
        """
        self.provider_id = provider_id or str(uuid.uuid4())
        self.name = name or self.__class__.__name__
        self.config = config or {}
        # self.logger = logging.getLogger(f"Provider.{self.name}")
        self.logger = logger
        self.cache = TTLCache(maxsize=1, ttl=60*20)


    @abstractmethod
    async def get_assets(self) -> List[Tuple[str, float]]:
        """
        获取资产列表，所有子类必须实现此方法

        返回:
            List[Tuple[str, float]]: 资产列表，每项为(资产ID, 数量)元组
        """
        pass

    @abstractmethod
    def validate_assets(self, assets: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """
        验证资产列表的格式和内容

        参数:
            assets: 原始资产列表

        返回:
            验证后的资产列表
        """
        pass

    async def initialize(self) -> bool:
        """
        初始化供货商，子类可以重写此方法进行额外的初始化

        返回:
            bool: 初始化是否成功
        """
        return True

    def shutdown(self) -> None:
        """
        关闭供货商，子类可以重写此方法进行清理工作
        """
        pass


# third_provider.py (续)
import traceback


class ProviderManager:
    """
    第三方供货者管理类
    负责注册、初始化和管理供货商对象
    使用依赖注入方式注册provider实例
    """

    def __init__(self):
        """
        初始化供货者管理器
        """
        self.providers = {}  # provider_id -> Provider实例
        # self.logger = logging.getLogger("ProviderManager")
        self.logger = logger

    async def register_provider(self, provider: Provider) -> bool:
        """
        注册已实例化的Provider对象

        参数:
            provider: Provider实例

        返回:
            bool: 注册是否成功
        """
        if not isinstance(provider, Provider):
            self.logger.error(f"Object is not a Provider instance: {type(provider).__name__}")
            return False

        # 检查provider_id是否已存在
        if provider.provider_id in self.providers:
            self.logger.warning(f"Provider with ID '{provider.provider_id}' already registered, will be replaced")

        # 尝试初始化provider
        try:
            if not await provider.initialize():
                self.logger.error(f"Failed to initialize provider {provider.name}")
                return False
            
            # 存储provider实例
            self.providers[provider.provider_id] = provider
            self.logger.info(f"Registered provider: {provider.name} ({provider.provider_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing provider '{provider.name}': {e}")
            self.logger.debug(traceback.format_exc())
            return False

    async def register_providers(self, providers: List[Provider]) -> Dict[str, bool]:
        """
        批量注册多个Provider实例

        参数:
            providers: Provider实例列表

        返回:
            Dict[str, bool]: 每个provider的注册结果，键为provider_id
        """
        results = {}
        for provider in providers:
            results[provider.provider_id] = await self.register_provider(provider)
        
        success_count = sum(1 for result in results.values() if result)
        self.logger.info(f"Registered {success_count}/{len(providers)} providers")
        return results

    def unregister_provider(self, provider_id: str) -> bool:
        """
        注销Provider实例

        参数:
            provider_id: Provider实例ID

        返回:
            bool: 注销是否成功
        """
        if provider_id not in self.providers:
            self.logger.warning(f"Provider with ID '{provider_id}' not found")
            return False

        try:
            # 关闭provider
            self.providers[provider_id].shutdown()
            # 移除provider
            del self.providers[provider_id]
            self.logger.info(f"Unregistered provider with ID '{provider_id}'")
            return True
        except Exception as e:
            self.logger.error(f"Error unregistering provider '{provider_id}': {e}")
            self.logger.debug(traceback.format_exc())
            return False

    def get_provider(self, provider_id: str) -> Optional[Provider]:
        """
        获取Provider实例

        参数:
            provider_id: Provider实例ID

        返回:
            Provider实例或None（如果不存在）
        """
        if provider_id not in self.providers:
            self.logger.warning(f"Provider with ID '{provider_id}' not found")
            return None

        return self.providers[provider_id]

    def get_all_providers(self) -> List[Provider]:
        """
        获取所有Provider实例

        返回:
            Provider实例列表
        """
        return list(self.providers.values())

    def get_providers_by_type(self, provider_type: Type[Provider]) -> List[Provider]:
        """
        获取特定类型的所有Provider实例

        参数:
            provider_type: Provider类型

        返回:
            符合指定类型的Provider实例列表
        """
        return [p for p in self.providers.values() if isinstance(p, provider_type)]

    async def get_all_assets(self) -> Dict[str, Dict[str, float]]:
        """
        获取所有Provider的资产

        返回:
            字典 {provider_id: {asset_id: quantity}}
        """
        result = {}

        for provider_id, provider in self.providers.items():
            try:
                assets = await provider.get_assets()
                result[provider.name] = {asset_id: qty for asset_id, qty in assets}
            except Exception as e:
                self.logger.error(f"Error getting assets from '{provider.name}': {e}")
                self.logger.debug(traceback.format_exc())

        return result

    def shutdown_all(self) -> None:
        """
        关闭所有Provider实例
        """
        for provider_id, provider in list(self.providers.items()):
            try:
                provider.shutdown()
                del self.providers[provider_id]
            except Exception as e:
                self.logger.error(f"Error shutting down provider '{provider.name}': {e}")

provider_manager = ProviderManager()