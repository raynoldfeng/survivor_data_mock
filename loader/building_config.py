import csv
from typing import Dict
from .enums import *

class BuildingConfig:
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
        self.slot_type: str = ""  # 新增：槽位类型

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'BuildingConfig':
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

        # 设置 slot_type
        if building.type == BuildingType.RESOURCE:
            building.slot_type = "resource"
        elif building.type == BuildingType.GENERAL:
            building.slot_type = "general"
        elif building.type == BuildingType.DEFENSE:
            building.slot_type = "defense"

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

    def get_next_level_id(self):
        """获取下一级建筑的 ID"""
        current_level = self.level
        next_level = current_level + 1
        current_id_parts = self.building_id.split('.')
        current_id_parts[-1] = f"level{next_level}"
        return '.'.join(current_id_parts)

    def get_upgrade_cost(self, all_buildings: Dict[str, 'BuildingConfig']):
        """获取升级所需的资源和数量"""
        next_level_id = self.get_next_level_id()
        next_level_building = all_buildings.get(next_level_id)
        if next_level_building:
            cost = {}
            for resource_id, modifier_dict in next_level_building.modifiers.items():
                for modifier, quantity in modifier_dict.items():
                    if modifier == Modifier.REDUCE:
                        cost[resource_id] = quantity
            return cost
        return {}

    def can_upgrade(self, player_resources: Dict[str, float], all_buildings: Dict[str, 'BuildingConfig']):
        """判断是否可以升级"""
        upgrade_cost = self.get_upgrade_cost(all_buildings)
        for resource_id, quantity in upgrade_cost.items():
            if player_resources.get(resource_id, 0) < quantity:
                return False
        return True


def load_buildings_from_csv(file_path: str) -> Dict[str, BuildingConfig]:
    buildings = {}
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            building = BuildingConfig.from_csv_row(row)
            buildings[building.building_id] = building
    return buildings