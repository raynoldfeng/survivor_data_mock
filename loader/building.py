from .imports import *
from .enums import *

class Building:
    def __init__(self):
        self.building_id: str = ""
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
        self.modifiers: Dict[str, Dict[Modifier, float]] = {}

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'Building':
        building = cls()
        building.building_id = row["id"]
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

        resource_id = row["resource_id"]
        modifier = Modifier(row["modifier"])
        quantity = float(row["quantity"])

        if resource_id not in building.modifiers:
            building.modifiers[resource_id] = {}
        building.modifiers[resource_id][modifier] = quantity

        return building

    @staticmethod
    def get_subtype(building_type: BuildingType, subtype_str: str):
        if building_type == BuildingType.RESOURCE:
            return ResourceSubType(subtype_str)
        elif building_type == BuildingType.GENERAL:
            return GeneralSubType(subtype_str)
        elif building_type == BuildingType.DEFENSE:
            return DefenseSubType(subtype_str)
        return None


def load_buildings_from_csv(file_path: str) -> Dict[str, Building]:
    buildings = {}
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            building = Building.from_csv_row(row)
            buildings[building.building_id] = building
    return buildings
