
from common import *
from .enums import *
from .modifier import ModifierConfig

class BuildingConfig:
    def __init__(self):
        self.config_id: str = ""
        self.name_id: str = ""
        self.type = None
        self.subtype = None
        self.level: int = 0
        self.build_period: int = 0
        self.manpower: int = 0
        self.durability: int = 0
        self.corruption: float = 0.0
        self.desc_id: str = ""
        self.defense_type = None
        self.defense_value: int = 0
        self.modifier_configs: List[ModifierConfig] = []  # 新增：存储 modifiers

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'BuildingConfig':
        building = cls()
        building.config_id = row["id"]
        building.name_id = row["name"]
        building.type = BuildingType(row["type"])
        building.subtype = cls.get_subtype(building.type, row.get("subtype", ""))
        building.level = int(row["level"])
        building.build_period = int(row["build_period"])
        building.manpower = int(row["manpower"])
        building.durability = int(row["durability"])
        building.corruption = float(row["corruption"])
        building.desc_id = row["desc"]

        if building.type == BuildingType.DEFENSE:
            building.defense_type = DefenseType(row["defense_type"])
            building.defense_value = int(row["defense_value"])

        return building

    @staticmethod
    def get_subtype(building_type: BuildingType, subtype_str: str):
        if building_type == BuildingType.RESOURCE:
            return BuildingSubTypeResource(subtype_str)
        elif building_type == BuildingType.GENERAL:
            return BuildingSubTypeGeneral(subtype_str)
        elif building_type == BuildingType.DEFENSE:
            return BuildingSubTypeDefense(subtype_str)
        return None
