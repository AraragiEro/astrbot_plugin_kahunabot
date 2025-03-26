from peewee import SqliteDatabase, DatabaseProxy
from peewee import Model
from peewee import FloatField, DecimalField, CharField, TextField, DateTimeField, BooleanField, IntegerField, DoubleField
from peewee import BigIntegerField
from peewee import SQL
from .connect import DatabaseConectManager, ConfigModel, CacheModel

__all__ = []

MODEL_LIST = []

class User(ConfigModel):
    user_qq = IntegerField(unique=True)
    create_date = DateTimeField()
    expire_date = DateTimeField()
    main_character_id = IntegerField()
DatabaseConectManager.add_model(User)

class UserData(ConfigModel):
    user_qq = IntegerField(unique=True)
    user_data = TextField()
    class Meta:
        table_name = 'user_data'
DatabaseConectManager.add_model(UserData)

class Character(ConfigModel):
    character_id = IntegerField(unique=True)
    character_name = TextField()
    QQ = IntegerField()
    create_date = DateTimeField()
    token = TextField()
    refresh_token = TextField()
    expires_date = DateTimeField()
    corp_id = IntegerField()
    director = BooleanField()

    class Meta:
        table_name = 'character'
DatabaseConectManager.add_model(Character)

class Structure(ConfigModel):
    structure_id = IntegerField(unique=True)
    name = CharField()
    owner_id = IntegerField()
    solar_system_id = IntegerField()
    type_id = IntegerField()
    system = IntegerField()
    mater_rig_level = IntegerField(null=True)
    time_rig_level = IntegerField(null=True)
    class Meta:
        table_name = 'structure'
DatabaseConectManager.add_model(Structure)

class AssetContainer(ConfigModel):
    asset_location_id = IntegerField()
    asset_location_type = CharField()
    structure_id = IntegerField()
    solar_system_id = IntegerField()
    asset_name = TextField()
    asset_owner_id = IntegerField()
    asset_owner_type = CharField()
    asset_owner_qq = IntegerField()
    tag = CharField(null=True)

    class Meta:
        table_name = 'asset_container'
        constraints = [SQL('UNIQUE(asset_location_id, asset_owner_qq)')]
DatabaseConectManager.add_model(AssetContainer)

# esi_cache
class Asset(CacheModel):
    asset_type = IntegerField()
    owner_id = IntegerField()
    is_blueprint_copy = BooleanField()
    is_singleton = BooleanField()
    item_id = BigIntegerField()
    location_flag = CharField()
    location_id = BigIntegerField()
    location_type = CharField()
    quantity = IntegerField()
    type_id = IntegerField()
    class Meta:
        table_name = 'asset'
DatabaseConectManager.add_model(Asset)

class AssetCache(CacheModel):
    asset_type = IntegerField()
    owner_id = IntegerField()
    is_blueprint_copy = BooleanField()
    is_singleton = BooleanField()
    item_id = BigIntegerField()
    location_flag = CharField()
    location_id = BigIntegerField()
    location_type = CharField()
    quantity = IntegerField()
    type_id = IntegerField()
    class Meta:
        table_name = 'asset_cache'
DatabaseConectManager.add_model(AssetCache)

class AssetOwner(ConfigModel):
    asset_owner_qq = IntegerField()
    asset_owner_id = IntegerField()
    asset_type = CharField()
    asset_access_character_id = IntegerField()
    class Meta:
        table_name = 'asset_owner'
DatabaseConectManager.add_model(AssetOwner)

class MarketOrder(CacheModel):
    duration = IntegerField()
    is_buy_order = BooleanField()
    issued = DateTimeField()
    location_id = IntegerField()
    min_volume = IntegerField()
    order_id = DecimalField()
    price = DecimalField()
    range = CharField()
    system_id = IntegerField(null=True)
    type_id = IntegerField()
    volume_remain = IntegerField()
    volume_total = IntegerField()

    class Meta:
        table_name = 'market_order'
DatabaseConectManager.add_model(MarketOrder)

class MarketOrderCache(CacheModel):
    duration = IntegerField()
    is_buy_order = BooleanField()
    issued = DateTimeField()
    location_id = IntegerField()
    min_volume = IntegerField()
    order_id = DecimalField()
    price = DecimalField()
    range = CharField()
    system_id = IntegerField(null=True)
    type_id = IntegerField()
    volume_remain = IntegerField()
    volume_total = IntegerField()

    class Meta:
        table_name = 'market_order_cache'
DatabaseConectManager.add_model(MarketOrderCache)

class IndustryJobs(CacheModel):
    activity_id = IntegerField()
    blueprint_id = BigIntegerField()
    blueprint_location_id = BigIntegerField()
    blueprint_type_id = IntegerField()
    completed_character_id = IntegerField(null=True)
    completed_date = DateTimeField(null=True)
    cost = DoubleField(null=True)
    duration = IntegerField()
    end_date = DateTimeField()
    facility_id = BigIntegerField()
    installer_id = IntegerField()
    job_id = IntegerField()
    licensed_runs = IntegerField(null=True)
    location_id = BigIntegerField() # station_id in character api return
    output_location_id = BigIntegerField()
    pause_date = DateTimeField(null=True)
    probability = FloatField(null=True)
    product_type_id = IntegerField(null=True)
    runs = IntegerField()
    start_date = DateTimeField()
    status = CharField()
    successful_runs = IntegerField(null=True)

    owner_id = IntegerField()

    class Meta:
        table_name = 'industry_jobs'
DatabaseConectManager.add_model(IndustryJobs)

class IndustryJobsCache(CacheModel):
    activity_id = IntegerField()
    blueprint_id = BigIntegerField()
    blueprint_location_id = BigIntegerField()
    blueprint_type_id = IntegerField()
    completed_character_id = IntegerField(null=True)
    completed_date = DateTimeField(null=True)
    cost = DoubleField(null=True)
    duration = IntegerField()
    end_date = DateTimeField()
    facility_id = BigIntegerField()
    installer_id = IntegerField()
    job_id = IntegerField()
    licensed_runs = IntegerField(null=True)
    location_id = BigIntegerField() # station_id in character api return
    output_location_id = BigIntegerField()
    pause_date = DateTimeField(null=True)
    probability = FloatField(null=True)
    product_type_id = IntegerField(null=True)
    runs = IntegerField()
    start_date = DateTimeField()
    status = CharField()
    successful_runs = IntegerField(null=True)

    owner_id = IntegerField()
    class Meta:
        table_name = 'industry_jobs_cache'
DatabaseConectManager.add_model(IndustryJobsCache)

class SystemCost(CacheModel):
    solar_system_id = IntegerField(primary_key=True)
    manufacturing = FloatField(null=True)
    researching_time_efficiency = FloatField(null=True)
    researching_material_efficiency = FloatField(null=True)
    copying = FloatField(null=True)
    invention = FloatField(null=True)
    reaction = FloatField(null=True)

    class Meta:
        table_name = "system_cost"
DatabaseConectManager.add_model(SystemCost)

class SystemCostCache(CacheModel):
    solar_system_id = IntegerField(primary_key=True)
    manufacturing = FloatField(null=True)
    researching_time_efficiency = FloatField(null=True)
    researching_material_efficiency = FloatField(null=True)
    copying = FloatField(null=True)
    invention = FloatField(null=True)
    reaction = FloatField(null=True)

    class Meta:
        table_name = "system_cost_cache"
DatabaseConectManager.add_model(SystemCostCache)

class BlueprintAsset(CacheModel):
    item_id = BigIntegerField(primary_key=True)
    location_flag = CharField()
    location_id = BigIntegerField()
    material_efficiency = IntegerField()
    quantity = IntegerField()
    runs = IntegerField()
    time_efficiency = IntegerField()
    type_id = IntegerField()

    owner_id = IntegerField()
    owner_type = CharField()
    class Meta:
        table_name = "blueprint_asset"
DatabaseConectManager.add_model(BlueprintAsset)

class BlueprintAssetCache(CacheModel):
    item_id = BigIntegerField(primary_key=True)
    location_flag = CharField()
    location_id = BigIntegerField()
    material_efficiency = IntegerField()
    quantity = IntegerField()
    runs = IntegerField()
    time_efficiency = IntegerField()
    type_id = IntegerField()

    owner_id = IntegerField()
    owner_type = CharField()
    class Meta:
        table_name = "blueprint_asset_cache"
DatabaseConectManager.add_model(BlueprintAssetCache)

class InvTypeMap(ConfigModel):
    maped_type = CharField(unique=True)
    target_type = CharField()
    class Meta:
        table_name = "inv_type_map"
DatabaseConectManager.add_model(InvTypeMap)

class Matcher(ConfigModel):
    matcher_name = CharField(unique=True)
    user_qq = IntegerField()
    matcher_type = CharField()
    matcher_data = TextField()
    class Meta:
        table_name = "matcher"
DatabaseConectManager.add_model(Matcher)

class MarketPrice(CacheModel):
    adjusted_price = IntegerField(null=True)
    average_price = IntegerField(null=True)
    type_id = IntegerField(primary_key=True)
    class Meta:
        table_name = "market_price"
DatabaseConectManager.add_model(MarketPrice)

class MarketPriceCache(CacheModel):
    adjusted_price = IntegerField(null=True)
    average_price = IntegerField(null=True)
    type_id = IntegerField(primary_key=True)
    class Meta:
        table_name = "market_price_cache"
DatabaseConectManager.add_model(MarketPriceCache)

class MarketHistory(ConfigModel):
    region_id = IntegerField()
    type_id = IntegerField()
    date = DateTimeField()
    average = IntegerField()
    highest = IntegerField()
    lowest = IntegerField()
    order_count = IntegerField()
    volume = IntegerField()
    class Meta:
        table_name = "market_history"
        indexes = (
            (('region_id', 'type_id', 'date'), True),
        )
DatabaseConectManager.add_model(MarketHistory)