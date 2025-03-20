from peewee import SqliteDatabase

from ...utils import KahunaException
from ..config_server.config import config

if config['APP']['DBTYPE'] == 'sqlite' and config['SQLITEDB']['DATADB']:
    db = SqliteDatabase(config['SQLITEDB']['DATADB'], pragmas={
        'journal_mode': 'wal',  # 启用 WAL 模式
        'cache_size': -1024 * 64,  # 调整缓存大小，单位为 KB
        'synchronous': 0  # 提高性能：异步写日志
    }, timeout=120)
else:
    raise KahunaException("bot db open failed")

db.connect()

class DatabaseConectManager():
    _connect_dict = {}

    @classmethod
    def init_connect(cls):
        cls.init_config_database()

    @classmethod
    def init_config_database(cls):
        if config['APP']['DBTYPE'] == 'sqlite' and config['SQLITEDB']['CONFIG_DB']:
            db = SqliteDatabase(config['SQLITEDB']['CONFIG_DB'], pragmas={
                'journal_mode': 'wal',  # 启用 WAL 模式
                'cache_size': -1024 * 64,  # 调整缓存大小，单位为 KB
                'synchronous': 0  # 提高性能：异步写日志
            }, timeout=120)

            db.connect()
            cls._connect_dict["config"] = db
        else:
            raise KahunaException("bot db open failed")

    @classmethod
    def init_cache_database(cls):
        if config['APP']['DBTYPE'] == 'sqlite' and config['SQLITEDB']['CACHE_DB']:
            db = SqliteDatabase(config['SQLITEDB']['CACHE_DB'], pragmas={
                'journal_mode': 'wal',  # 启用 WAL 模式
                'cache_size': -1024 * 64,  # 调整缓存大小，单位为 KB
                'synchronous': 0  # 提高性能：异步写日志
            }, timeout=120)

            db.connect()
            cls._connect_dict["cache"] = db
        else:
            raise KahunaException("bot db open failed")