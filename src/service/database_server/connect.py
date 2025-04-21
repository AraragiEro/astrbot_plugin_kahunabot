from peewee import SqliteDatabase, DatabaseProxy, Model

from ...utils import KahunaException
from ..config_server.config import config
from ..log_server import logger

config_db = DatabaseProxy()
cache_db = DatabaseProxy()
class ConfigModel(Model):
    class Meta:
        database = config_db

class CacheModel(Model):
    class Meta:
        database = cache_db

class DatabaseConectManager():
    _connect_dict = {
        'config': config_db,
        'cache': cache_db
    }
    _config_model_list = []
    _cache_model_list = []

    @classmethod
    def init(cls):
        cls.init_config_database()
        cls.init_cache_database()
        cls.create_default_table()
        # cls.clean_table_not_in_list()

    @classmethod
    def init_config_database(cls):
        if config['APP']['DBTYPE'] == 'sqlite' and config['SQLITEDB']['CONFIG_DB']:
            db = SqliteDatabase(config['SQLITEDB']['CONFIG_DB'], pragmas={
                'auto_vacuum': 'FULL',
                'journal_mode': 'wal',  # 启用 WAL 模式
                'cache_size': -1024 * 64,  # 调整缓存大小，单位为 KB
                'synchronous': 0  # 提高性能：异步写日志
            }, timeout=120)

            cls._connect_dict["config"].initialize(db)
            logger.info("链接配置数据库成功。")
        else:
            raise KahunaException("bot db open failed")

    @classmethod
    def init_cache_database(cls):
        if config['APP']['DBTYPE'] == 'sqlite' and config['SQLITEDB']['CACHE_DB']:
            db = SqliteDatabase(config['SQLITEDB']['CACHE_DB'], pragmas={
                'auto_vacuum': 'FULL',
                'journal_mode': 'wal',  # 启用 WAL 模式
                'cache_size': -1024 * 64,  # 调整缓存大小，单位为 KB
                'synchronous': 0  # 提高性能：异步写日志
            }, timeout=120)

            cls._connect_dict["cache"].initialize(db)
            logger.info("链接缓存数据库成功。")
        else:
            raise KahunaException("bot db open failed")

    @classmethod
    def config_db(cls) -> DatabaseProxy:
        return cls._connect_dict["config"]

    @classmethod
    def cache_db(cls) -> DatabaseProxy:
        return cls._connect_dict["cache"]

    @classmethod
    def add_model(cls, model, type: str = "config"):
        if issubclass(model, ConfigModel):
            cls._config_model_list.append(model)
        elif issubclass(model, CacheModel):
            cls._cache_model_list.append(model)
        else:
            logger.error(f"model {model} is not a subclass of ConfigModel or CacheModel")

    @classmethod
    def create_default_table(cls):
        for model in (cls._config_model_list + cls._cache_model_list):
            if not model.table_exists():
                logger.info(f"create table {model._meta.table_name}")
                model.create_table()

        logger.info("创建默认表结构成功.")

    @classmethod
    def clean_table_not_in_list(cls):
        # 获取 model_list 中所有表的名称
        config_model_tables = {model._meta.table_name for model in cls._config_model_list}
        cache_model_table = {model._meta.table_name for model in cls._cache_model_list}
        # 处理 config 数据库
        try:
            config_db = cls._connect_dict["config"]
            if not config_db.is_closed():
                config_tables = set(config_db.get_tables())
                # 找出需要删除的表（在数据库中存在但不在 model_list 中的表）
                tables_to_delete = config_tables - config_model_tables

                # 删除不需要的表
                for table in tables_to_delete:
                    logger.info(f"清理不需要的数据表{table}")
                    config_db.execute_sql(f'DROP TABLE IF EXISTS "{table}"')
        except Exception as e:
            logger.error(f"清理 config 数据库表时出错: {str(e)}")

        # 处理 cache 数据库
        try:
            cache_db = cls._connect_dict["cache"]
            if not cache_db.is_closed():
                cache_tables = set(cache_db.get_tables())
                # 找出需要删除的表
                tables_to_delete = cache_tables - cache_model_table

                # 删除不需要的表
                for table in tables_to_delete:
                    logger.info(f"清理不需要的数据表{table}")
                    cache_db.execute_sql(f'DROP TABLE IF EXISTS "{table}"')
        except Exception as e:
            logger.error(f"清理 cache 数据库表时出错: {str(e)}")

        # try:
        #     for db_name, db in cls._connect_dict.items():
        #         if not db.is_closed():
        #             # 切换日志模式
        #             db.execute_sql('PRAGMA journal_mode=DELETE;')
        #             # 执行VACUUM
        #             db.execute_sql('VACUUM;')
        #             # 恢复WAL模式
        #             db.execute_sql('PRAGMA journal_mode=WAL;')
        #             logger.info(f"已对 {db_name} 数据库执行VACUUM操作")
        # except Exception as e:
        #     logger.error(f"执行VACUUM时出错: {str(e)}")