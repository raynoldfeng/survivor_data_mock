from .imports import *
from .enums import *

class Building:
    def __init__(self):
        self.building_id: str = ""
        self.name_id: str = ""
        self.type: Optional[BuildingType] = None
        self.subtype: Union[None, ResourceSubType, GeneralSubType, DefenseSubType] = None
        self.level: int = 0
        self.build_period: int = 0
        self.manpower: int = 0
        self.durability: int = 0
        self.corruption: float = 0.0
        self.desc_id: str = ""
        self.defense_type: Optional[DefenseType] = None
        self.defense_value: int = 0
        self.modifiers: Dict[str, Dict[ModifierType, float]] = {}

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'Building':
        building_type = BuildingType(row["type"])
        if building_type == BuildingType.DEFENSE:
            building = DefenseBuilding()
        else:
            building = Building()

        building.building_id = row["id"]
        building.name_id = row["name"]
        building.type = building_type
        building.subtype = cls.get_subtype(building_type, row.get("subtype", ""))
        building.level = int(row["level"])
        building.build_period = int(row["build_period"])
        building.manpower = int(row["manpower"])
        building.durability = int(row["durability"])
        building.corruption = float(row["corruption"])
        building.desc_id = row["desc"]
        if building_type == BuildingType.DEFENSE:
            building.defense_type = DefenseType(row["defense_type"])
            building.defense_value = int(row["defense_value"])

        resource_id = row["resource_id"]
        modifier_type = ModifierType(row["resource_modifier"])
        quantity = float(row["quantity"])

        if resource_id not in building.modifiers:
            building.modifiers[resource_id] = {}
        building.modifiers[resource_id][modifier_type] = quantity

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


class DefenseBuilding(Building):
    def __init__(self):
        super().__init__()


def load_buildings_from_csv(file_path: str) -> Dict[str, Building]:
    buildings = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                building_id = row["id"]
                if building_id not in buildings:
                    building = Building.from_csv_row(row)
                    buildings[building_id] = building
                else:
                    resource_id = row["resource_id"]
                    modifier_type = ModifierType(row["resource_modifier"])
                    quantity = float(row["quantity"])
                    if resource_id not in buildings[building_id].modifiers:
                        buildings[building_id].modifiers[resource_id] = {}
                    buildings[building_id].modifiers[resource_id][modifier_type] = quantity

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
    except Exception as e:
        print(f"Error loading buildings from CSV: {e}")
    return buildings