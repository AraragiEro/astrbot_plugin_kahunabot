import asyncio

from playhouse.shortcuts import model_to_dict

from ..database_server.model import Structure as M_Structure
from ..log_server import logger
from ...service.sde_service.database import MapSolarSystems
from ..evesso_server.eveesi import universe_stations_station, universe_structures_structure


STRUCTURE_MEMBER = {"structure_id", "name", "owner_id", "solar_system_id", "type_id", "system"}


class Structure:
    mater_rig_level = 0
    time_rig_level = 0
    def __init__(self, structure_id: int, name: str, owner_id: int, solar_system_id: int, type_id: int, system: str,
                 mater_rig_level=0, time_rig_level=0):
        self.structure_id = structure_id
        self.name = name
        self.owner_id = owner_id
        self.solar_system_id = solar_system_id
        self.type_id = type_id
        self.system = system
        self.time_rig_level = time_rig_level
        self.mater_rig_level = mater_rig_level

    def get_from_db(self):
        return M_Structure.get_or_none(M_Structure.structure_id == self.structure_id)

    def insert_to_db(self):
        obj = self.get_from_db()
        if not obj:
            obj = M_Structure()

        obj.structure_id = self.structure_id
        obj.name = self.name
        obj.owner_id = self.owner_id
        obj.solar_system_id = self.solar_system_id
        obj.type_id = self.type_id
        obj.system = self.system
        obj.mater_rig_level = self.mater_rig_level
        obj.time_rig_level = self.time_rig_level

        obj.save()

    def __iter__(self):
        yield 'structure_id', self.structure_id
        yield 'name', self.name
        yield 'owner_id', self.owner_id
        yield 'solar_system_id', self.solar_system_id
        yield 'type_id', self.type_id
        yield 'system', self.system
        yield 'mater_rig_level', self.mater_rig_level
        yield 'time_rig_level', self.time_rig_level


class StructureManager():
    structure_dict = dict()
    init_status = False

    @classmethod
    def init(cls):
        cls.init_structure_dict()

    @classmethod
    def init_structure_dict(cls):
        if not cls.init_status:
            for structure_data in M_Structure.select():
                data = model_to_dict(structure_data)
                data.pop('id')
                structure = Structure(**data)
                cls.structure_dict[structure.structure_id] = structure
            cls.init_status = True

        logger.info(f"init structure dict complete. {id(cls)}")

    @classmethod
    def get_all_structure(cls):
        return [structure for structure in cls.structure_dict.values()]

    @classmethod
    def get_structure(cls, structure_id: int, ac_token=None) -> Structure | None:
        structure = cls.structure_dict.get(structure_id, None)
        if not structure and ac_token:
            structure = cls.get_new_structure_info(structure_id, ac_token=ac_token)
        return structure

    @classmethod
    def get_new_structure_info(cls, structure_id: int, ac_token: str = None) -> dict:
        """
        "name": "4-HWWF - WinterCo. Central Station",
        "owner_id": 98599770,
        "position": {
            "x": -439918627801.0,
            "y": -86578525155.0,
            "z": -1177327092030.0
        },
        "solar_system_id": 30000240,
        "type_id": 35834,
        "system": "4-HWWF"
        'structure_id': 1035466617946
        """
        info = None
        if len(str(structure_id)) <= 8:
            info = universe_stations_station(structure_id)
        elif ac_token:
            info = universe_structures_structure(ac_token, structure_id)
        else:
            raise ValueError("universe_structures_structure need ac_token.")
        if not info:
            return None
        info.update({
            'system': MapSolarSystems.get(MapSolarSystems.solarSystemID == info[
                ('solar_system_id' if len(str(structure_id)) > 8 else 'system_id')])
            .solarSystemName
        })

        # 处理数据差异
        if "owner_id" not in info:
            info["owner_id"] = info["owner"]
        if "solar_system_id" not in info:
            info["solar_system_id"] = info['system_id']
        info["structure_id"] = structure_id

        structure_info = {k:v for k,v in info.items() if k in STRUCTURE_MEMBER}

        new_structure = Structure(**structure_info)
        cls.structure_dict[structure_id] = new_structure
        new_structure.insert_to_db()

        return new_structure
