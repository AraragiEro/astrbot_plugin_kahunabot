from .model import MarketOrderCache, MarketHistory
from . import model
from datetime import datetime, timedelta

from ...utils import get_beijing_utctime
from ..log_server import logger

class database_utils:
    @classmethod
    def get_order_in_location(cls, location_id: int):
        return MarketOrderCache.select().where(MarketOrderCache.location_id == location_id)

class RefreshDateUtils():
    model = model.RefreshDate

    @classmethod
    def create_refresh_date(cls, id: str):
        """
        创建或更新刷新日期记录

        Args:
            id: 记录的唯一标识符

        Returns:
            RefreshDate: 创建或更新的刷新日期记录
        """
        try:
            refresh_date = get_beijing_utctime(datetime.now())
            # 尝试查找是否已存在该id的记录
            existing_record = cls.model.get_or_none(cls.model.id == id)

            if existing_record:
                # 如果记录存在，更新刷新日期
                existing_record.date = refresh_date
                existing_record.save()
                return existing_record
            else:
                # 如果记录不存在，创建新记录
                new_record = cls.model.create(id=id, date=refresh_date)
                return new_record
        except Exception as e:
            # 处理可能发生的异常
            logger.error(f"创建或更新刷新日期记录时发生错误: {e}")
            raise

    @classmethod
    def out_of_min_interval(cls, id: str, time_interval_min: int):
        try:
            time_interval = timedelta(minutes=time_interval_min)
            refresh_date = cls.model.get_or_none(cls.model.id == id)
            if not refresh_date:
                logger.info(f"refresh_date not found, create refresh_date: {id}")
                cls.create_refresh_date(id)
                return True
            # logger.info(f"now - refresh_date: {get_beijing_utctime(datetime.now()) - refresh_date.date}")
            return get_beijing_utctime(datetime.now()) - refresh_date.date > time_interval
        except Exception as e:
            logger.error(e)
            raise

    @classmethod
    def out_of_day_interval(cls, id: str, time_interval_day: int):
        try:
            refresh_date = cls.model.get_or_none(cls.model.id == id)
            if not refresh_date:
                cls.create_refresh_date(id)
                return True

            # 获取当前北京时间
            current_date = get_beijing_utctime(datetime.now()).date()
            # 获取上次刷新的日期部分
            last_refresh_date = refresh_date.date.date()

            # 计算日期差
            days_diff = (current_date - last_refresh_date).days

            # 判断是否超过指定的天数间隔
            return days_diff >= time_interval_day
        except Exception as e:
            logger.error(e)
            raise

    @classmethod
    def out_of_hour_interval(cls, id: str, time_interval_hour: int):
        try:
            refresh_date = cls.model.get_or_none(cls.model.id == id)
            if not refresh_date:
                cls.create_refresh_date(id)
                return True

            # 获取当前北京时间
            current_time = get_beijing_utctime(datetime.now())
            # 获取上次刷新的时间
            last_refresh_time = refresh_date.date

            # 如果是不同的日期，直接计算完整的小时差
            if current_time.date() != last_refresh_time.date():
                # 计算天数差
                days_diff = (current_time.date() - last_refresh_time.date()).days
                # 计算小时差
                hour_diff = current_time.hour + (24 - last_refresh_time.hour) + (days_diff - 1) * 24
            else:
                # 同一天，直接比较小时部分
                hour_diff = current_time.hour - last_refresh_time.hour

            # 判断是否超过指定的小时间隔
            return hour_diff >= time_interval_hour
        except Exception as e:
            logger.error(e)
            raise

    @classmethod
    def update_refresh_date(cls, id: str):
        refresh_date = get_beijing_utctime(datetime.now())
        cls.model.update(date=refresh_date).where(cls.model.id == id).execute()

class UserAssetStatisticsUtils():
    model = model.UserAssetStatistics

    @classmethod
    def update(cls, user_qq, date, asset_data):
        # 使用 replace 方法实现 upsert
        cls.model.replace(
            user_qq=user_qq,
            date=date,
            asset_statistics=asset_data
        ).execute()

    @classmethod
    def get_user_asset_statistics(cls, user_qq):
        try:
            result = cls.model.select().where(cls.model.user_qq == user_qq)
            return result
        except cls.model.DoesNotExist:
            return None