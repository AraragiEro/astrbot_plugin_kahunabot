from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON, UniqueConstraint, \
    BigInteger
from sqlalchemy.ext.declarative import declarative_base

from .connect_manager import ConfigModel

class User(ConfigModel):
    __tablename__ = 'user'
    user_qq = Column(Integer, primary_key=True)
    create_date = Column(DateTime)
    expire_date = Column(DateTime)
    main_character_id = Column(Integer)

class UserData(ConfigModel):
    __tablename__ = 'user_data'
    user_qq = Column(Integer, primary_key=True)
    user_data = Column(Text)

class Character(ConfigModel):
    __tablename__ = 'character'
    character_id = Column(Integer, primary_key=True)
    character_name = Column(Text)
    QQ = Column(Integer)
    create_date = Column(DateTime)
    token = Column(Text)
    refresh_token = Column(Text)
    expires_date = Column(DateTime)
    corp_id = Column(Integer)
    director = Column(Boolean)

class Structure(ConfigModel):
    __tablename__ = 'structure'
    structure_id = Column(Integer, primary_key=True)
    name = Column(Text)
    owner_id = Column(Integer)
    solar_system_id = Column(Integer)
    type_id = Column(Integer)
    system = Column(Integer)
    mater_rig_level = Column(Integer, nullable=True)
    time_rig_level = Column(Integer, nullable=True)

class AssetContainer(ConfigModel):
    __tablename__ = 'asset_container'
    asset_location_id = Column(Integer, primary_key=True)
    asset_location_type = Column(Text)
    structure_id = Column(Integer)
    solar_system_id = Column(Integer)
    asset_name = Column(Text)
    asset_owner_id = Column(Integer)
    asset_owner_type = Column(Text)
    asset_owner_qq = Column(Integer)
    tag = Column(Text, nullable=True)
    # 定义联合唯一约束
    __table_args__ = (
        UniqueConstraint('asset_location_id', 'asset_owner_qq', name='uix_location_owner'),
    )

class AssetOwner(ConfigModel):
    __tablename__ = 'asset_owner'
    id = Column(Integer, primary_key=True)
    asset_owner_qq = Column(Integer)
    asset_owner_id = Column(Integer)
    asset_type = Column(Text)
    asset_access_character_id = Column(Integer)

class InvTypeMap(ConfigModel):
    __tablename__ = "inv_type_map"
    id = Column(Integer, primary_key=True)
    maped_type = Column(Text, unique=True)
    target_type = Column(Text)

class Matcher(ConfigModel):
    __tablename__ = "matcher"
    id = Column(Integer, primary_key=True)
    matcher_name = Column(Text, unique=True)
    user_qq = Column(Integer)
    matcher_type = Column(Text)
    matcher_data = Column(Text)

class UserAssetStatistics(ConfigModel):
    __tablename__ = "user_asset_statistics"
    id = Column(Integer, primary_key=True)
    user_qq = Column(Integer)
    date = Column(DateTime)
    asset_statistics = Column(Text)
    __table_args__ = (
        UniqueConstraint('user_qq', 'date', name='UserAssetStatistics_user_qq_date_unique'),
    )