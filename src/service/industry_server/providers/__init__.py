from .google_sheet_provider import GoogleSheetsProvider, YueseProvider
from ..third_provider import provider_manager
from ...config_server import config

proxy = config['APP']['PROXY']

async def init_providers():
    pl_provider = GoogleSheetsProvider(
        provider_id='PL',
        name='PL',
        config={
            'sheet_id': '1nvivMpLoci6z0dj0EBZu4mMu7YBiBGktTKTULmQQlXE',
            'sheet_name': [
                'Moon goos',
                'Minerals',
                'PI',
                'Ice',
                'Gas',
                'Salvage'
            ],
            'proxy': proxy,
            'id_column': 'type_id',
            'quantity_column': 'quantity'
        }
    )

    yuese_provider = YueseProvider(
        provider_id='Yuese',
        name='Yuese',
        config={
            'sheet_id': '15mCAFk_EVpYcEDyO3i-7WjxHZbn6lZB1SN0AiICzrVE',
            'sheet_name': ['仓库筛选'],
            'proxy': proxy,
            'id_column': '英名',
            'quantity_column': '数量'
        }
    )

    await provider_manager.register_providers([
        pl_provider,
        yuese_provider
    ])