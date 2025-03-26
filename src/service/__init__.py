from .asset_server.asset_manager import AssetManager
from .character_server.character_manager import CharacterManager
from .database_server.connect import DatabaseConectManager
from .industry_server.industry_config import IndustryConfigManager
from .industry_server.structure import StructureManager
from .market_server.market_manager import MarketManager
from .user_server.user_manager import UserManager

def init_server():
    DatabaseConectManager.init()
    CharacterManager.init()
    UserManager.init()
    StructureManager.init()
    AssetManager.init()
    IndustryConfigManager.init()
    MarketManager.init()
