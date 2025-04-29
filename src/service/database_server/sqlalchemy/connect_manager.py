from datetime import datetime
from typing import List, AnyStr
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import event

from ...config_server.config import config
from ...log_server import logger

ConfigModel = declarative_base()
CacheModel = declarative_base()

class DatabaseManager():
    def __init__(self):
        self.sessions = {}
        self.engines = {}

    async def create_default_table(self, conn, table_name: str):
        """创建默认表结构，使用传入的连接对象而不是创建新连接"""
        if table_name == 'config':
            await conn.run_sync(ConfigModel.metadata.create_all)
            logger.info('创建config默认表完成')
        elif table_name == 'cache':  # 使用 elif 而不是第二个 if
            await conn.run_sync(CacheModel.metadata.create_all)
            logger.info('创建cache默认表完成')

    async def create_async_session(self, database_path: AnyStr, database_name: AnyStr):
        database_url = f'sqlite+aiosqlite:///{database_path}'
        connect_args = {
            "check_same_thread": False,
            "timeout": 30,
            "uri": True,
            "isolation_level": None
        }

        engine = create_async_engine(
            database_url,
            connect_args=connect_args,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # 添加连接健康检查
            pool_recycle=3600,  # 连接回收时间
            echo=False,  # 生产环境关闭 SQL 日志
            future=True  # 使用新的 SQLAlchemy 2.0 API

        )

        # 设置 SQLite 优化
        # 使用同步引擎事件
        @event.listens_for(engine.sync_engine, "connect")
        def configure_connection(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA page_size=4096")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

        # 创建表
        async with engine.begin() as conn:
            await self.create_default_table(conn, database_name)

        self.sessions[database_name] = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        return self.sessions[database_name]

    @property
    def cache_session(self):
        return self.sessions['cache']

    @property
    def config_session(self):
        return self.sessions['config']

    def async_session(self, model):
        if issubclass(model, ConfigModel):
            return self.config_session
        elif issubclass(model, CacheModel):
            return self.cache_session
        else:
            raise Exception(
                f"model {model} is not in database session"
            )

    async def init(self):
        logger.info("初始化异步数据库")
        cache_db_path = config['SQLITEDB']['CACHE_DB']
        config_db_path = config['SQLITEDB']['CONFIG_DB']
        await self.create_async_session(config_db_path, 'config')
        await self.create_async_session(cache_db_path, 'cache')

        logger.info("数据库初始化完成")

database_manager = DatabaseManager()