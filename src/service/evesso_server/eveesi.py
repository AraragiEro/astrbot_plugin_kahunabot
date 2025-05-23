from logging import exception

import requests
from cachetools import TTLCache, cached
import traceback
import aiohttp
import asyncio
from typing import Optional, Any

# kahuna logger
from ..log_server import logger

permission_set = set()


async def get_request_async(url, headers=None, params=None, log=True, max_retries=2, timeout=60) -> Optional[Any]:
    """
    异步发送GET请求，带有重试机制

    Args:
        url: 请求URL
        headers: 请求头
        params: 查询参数
        log: 是否记录日志
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
    """
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if response.status == 200:
                        try:
                            data = await asyncio.wait_for(response.json(), timeout=timeout)
                            return data
                        except asyncio.TimeoutError:
                            if log:
                                logger.warning(f"JSON解析超时 (尝试 {attempt + 1}/{max_retries}): {url}")
                            if attempt == max_retries - 1:
                                raise
                            continue
                    else:
                        response_text = await response.text()
                        if log:
                            logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {url}")
                            logger.warning(f'{response.status}:{response_text}')
                        if attempt == max_retries - 1:
                            return None
                        await asyncio.sleep(1 * (attempt + 1))  # 指数退避
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if log:
                logger.error(f"请求异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                if log:
                    logger.error(traceback.format_exc())
                return None
            await asyncio.sleep(1 * (attempt + 1))  # 指数退避
        except Exception as e:
            if log:
                logger.error(traceback.format_exc())
            return None

async def verify_token(access_token, log=True):
    return await get_request_async("https://esi.evetech.net/verify/", headers={"Authorization": f"Bearer {access_token}"}, log=log)

async def character_character_id_skills(access_token, character_id, log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/characters/{character_id}/skills/",
                       headers={"Authorization": f"Bearer {access_token}"}, log=log)

async def character_character_id_wallet(access_token, character_id, log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/characters/{character_id}/wallet/",
                       headers={"Authorization": f"Bearer {access_token}"}, log=log)

async def character_character_id_portrait(access_token, character_id, log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/characters/{character_id}/portrait/",
                       headers={"Authorization": f"Bearer {access_token}"}, log=log)

async def characters_character_id_blueprints(page:int, access_token: str, character_id: int, log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/characters/{character_id}/blueprints/",
                       headers={"Authorization": f"Bearer {access_token}"}, params={"page": page}, log=log, max_retries=1)

async def industry_systems(log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/industry/systems/", log=log)

async def markets_structures(page: int, access_token: str, structure_id: int, log=True) -> dict:
    return await get_request_async(f"https://esi.evetech.net/latest/markets/structures/{structure_id}/",
                       headers={"Authorization": f"Bearer {access_token}"}, params={"page": page}, log=log, max_retries=1)

async def markets_region_orders(page: int, region_id: int, type_id: int = None, log=True):
    params = {"page": page}
    if type_id is not None:
        params["type_id"] = type_id
    return await get_request_async(
        f"https://esi.evetech.net/latest/markets/{region_id}/orders/", headers={},
       params=params, log=log, max_retries=1
    )

async def characters_character_assets(page: int, access_token: str, character_id: int, log=True):
    """

    """
    return await get_request_async(f"https://esi.evetech.net/latest/characters/{character_id}/assets/",
                       headers={"Authorization": f"Bearer {access_token}"}, params={"page": page}, log=log, max_retries=1)

CHARACRER_INFO_CACHE = TTLCache(maxsize=10, ttl=1200)
@cached(CHARACRER_INFO_CACHE)
async def characters_character(character_id, log=True):
    """
# alliance_id - Integer
# birthday -  String (date-time)
# bloodline_id - Integer
# corporation_id - Integer
# description - String
# faction_id - Integer
# gender - String
# name - String
# race_id - Integer
# security_status - Float (min: -10, max: 10)
# title - String
    """
    return await get_request_async(f"https://esi.evetech.net/latest/characters/{character_id}/", log=log)

async def corporations_corporation_assets(page: int, access_token: str, corporation_id: int, log=True):
    """
    # is_blueprint_copy - Boolean
    # is_singleton - Boolean
    # item_id - Integer
    # location_flag - String
    # location_id - Integer
    # location_type - String
    # quantity - Integer
    # type_id - Integer
    """
    return await get_request_async(f"https://esi.evetech.net/latest/corporations/{corporation_id}/assets/",
                       headers={"Authorization": f"Bearer {access_token}"}, params={"page": page}, log=log, max_retries=1)

async def corporations_corporation_id_roles(access_token: str, corporation_id: int, log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/corporations/{corporation_id}/roles/",
                       headers={"Authorization": f"Bearer {access_token}"}, log=log, max_retries=1)

async def corporations_corporation_id_industry_jobs(page: int, access_token: str, corporation_id: int, include_completed: bool = False, log=True):
    return await get_request_async(
    f"https://esi.evetech.net/latest/corporations/{corporation_id}/industry/jobs/",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "page": page,
            "include_completed": 1 if include_completed else 0
        }, log=log)

async def corporations_corporation_id_blueprints(page: int, access_token: str, corporation_id: int, log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/corporations/{corporation_id}/blueprints/",
                       headers={"Authorization": f"Bearer {access_token}"}, params={"page": page}, log=log, max_retries=1)

async def universe_structures_structure(access_token: str, structure_id: int, log=True):
    """
    name*	string
    owner_id    int32
    position
        x
        y
        z
    solar_system_id
    type_id
    """
    return await get_request_async(f"https://esi.evetech.net/latest/universe/structures/{structure_id}/",
                       headers={"Authorization": f"Bearer {access_token}"}, log=log)

async def universe_stations_station(station_id, log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/universe/stations/{station_id}/", log=log)

async def characters_character_id_industry_jobs(access_token: str, character_id: int, include_completed: bool = False, log=True):
    """
    List character industry jobs
    Args:
        access_token: Access token
        character_id: An EVE character ID
        datasource: The server name you would like data from
        include_completed: Whether to retrieve completed character industry jobs
    Returns:
        Industry jobs placed by a character
    """
    return await get_request_async(f"https://esi.evetech.net/latest/characters/{character_id}/industry/jobs/", headers={
        "Authorization": f"Bearer {access_token}"
    }, params={
        "include_completed": 1 if include_completed else 0
    }, log=log)


async def markets_prices(log=True):
    return await get_request_async(f'https://esi.evetech.net/latest/markets/prices/', log=log)

# /markets/{region_id}/history/
async def markets_region_history(region_id: int, type_id: int, log=True):
    return await get_request_async(f"https://esi.evetech.net/latest/markets/{region_id}/history/", headers={},
                       params={"type_id": type_id, "region_id": region_id}, log=log, max_retries=1)

# /characters/{character_id}/orders/
async def characters_character_orders(access_token, character_id: int, log=True):
    return await get_request_async(
        f"https://esi.evetech.net/latest/characters/{character_id}/orders/",
        headers={"Authorization": f"Bearer {access_token}"},
        log=log
    )

# /characters/{character_id}/orders/history/
async def characters_character_orders_history(page: int, access_token, character_id: int, log=True):
    return await get_request_async(
        f"https://esi.evetech.net/latest/characters/{character_id}/orders/history/",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page": page},
        log=log,
        max_retries=1
    )

# /characters/{character_id}/portrait/
async def characters_character_portrait(character_id: int, log=True):
    return await get_request_async(
        f"https://esi.evetech.net/latest/characters/{character_id}/portrait/",
        log=log
    )