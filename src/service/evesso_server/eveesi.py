import requests
from cachetools import TTLCache, cached
import traceback

# kahuna logger

permission_set = set()

def get_request(url, headers=dict(), params=dict()):
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data  # 注意：实际的键可能不同，请参考 ESI 文档
    else:
        print(response.text)
        return None

def verify_token(access_token):
    return get_request(
        "https://esi.evetech.net/verify/",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def character_character_id_skills(access_token, character_id):
    return get_request(
        f"https://esi.evetech.net/latest/characters/{character_id}/skills/",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def character_character_id_wallet(access_token, character_id):
    return get_request(
        f"https://esi.evetech.net/latest/characters/{character_id}/wallet/",
        headers={"Authorization": f"Bearer {access_token}"}
    )


def character_character_id_portrait(access_token, character_id):
    return get_request(
        f"https://esi.evetech.net/latest/characters/{character_id}/portrait/",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def characters_character_id_blueprints(page:int, access_token: str, character_id: int):
    return get_request(
        f"https://esi.evetech.net/latest/characters/{character_id}/blueprints/",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page": page}
    )

def industry_systems():
    return get_request(
        f"https://esi.evetech.net/latest/industry/systems/"
    )

def markets_structures(page: int, access_token: str, structure_id: int) -> dict:
    return get_request(
        f"https://esi.evetech.net/latest/markets/structures/{structure_id}/",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page": page}
    )

def markets_region_orders(page: int, region_id: int, type_id: int =None):
    return get_request(
        f"https://esi.evetech.net/latest/markets/{region_id}/orders/",
        headers={},
        params={"page": page, "type_id": type_id}
    )

def characters_character_assets(page: int, access_token: str, character_id: int):
    """

    """
    return get_request(
        f"https://esi.evetech.net/latest/characters/{character_id}/assets/",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page": page}
    )

CHARACRER_INFO_CACHE = TTLCache(maxsize=10, ttl=1200)
@cached(CHARACRER_INFO_CACHE)
def characters_character(character_id):
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
    return get_request(
        f"https://esi.evetech.net/latest/characters/{character_id}/"
    )

def corporations_corporation_assets(page: int, access_token: str, corporation_id: int):
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
    return get_request(
        f"https://esi.evetech.net/latest/corporations/{corporation_id}/assets/",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page": page}
    )

def corporations_corporation_id_roles(access_token: str, corporation_id: int):
    return get_request(
        f"https://esi.evetech.net/latest/corporations/{corporation_id}/roles/",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def corporations_corporation_id_industry_jobs(page: int, access_token: str, corporation_id: int, include_completed: bool = False):
    return get_request(
        f"https://esi.evetech.net/latest/corporations/{corporation_id}/industry/jobs/",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "page": page,
            "include_completed": include_completed
        }
    )

def corporations_corporation_id_blueprints(page: int, access_token: str, corporation_id: int):
    return get_request(
        f"https://esi.evetech.net/latest/corporations/{corporation_id}/blueprints/",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page": page}
    )

def universe_structures_structure(access_token: str, structure_id: int):
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
    return get_request(
        f"https://esi.evetech.net/latest/universe/structures/{structure_id}/",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def universe_stations_station(station_id):
    return get_request(
        f"https://esi.evetech.net/latest/universe/stations/{station_id}/"
    )

def characters_character_id_industry_jobs(access_token: str, character_id: int, include_completed: bool = False):
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
    return get_request(
        f"https://esi.evetech.net/latest/characters/{character_id}/industry/jobs/",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params={
            "include_completed": include_completed
        }
    )


def markets_prices():
    return get_request(
        f'https://esi.evetech.net/latest/markets/prices/'
    )

# /markets/{region_id}/history/
def markets_region_history(region_id: int, type_id: int):
    return get_request(
        f"https://esi.evetech.net/latest/markets/{region_id}/history/",
        headers={},
        params={"type_id": type_id, "region_id": region_id}
    )

