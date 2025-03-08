import csv
from typing import Dict, List
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
        self.modifiers: List[Dict[str, str]] = []  # 新增：存储 modifiers

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

# 新增 BuildingDataMapper
class BuildingDataMapper:
    @staticmethod
    def map_building_info(row):
        return {
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'subtype': row['subtype'],
            'level': int(row['level']),
            'build_period': int(row['build_period']),
            'manpower': int(row['manpower']),
            'durability': int(row['durability']),
            'corruption': float(row['corruption']),
            'desc': row['desc'],
            'defense_type': row.get('defense_type'),  # 可选
            'defense_value': int(row['defense_value']) if row.get('defense_value') else None  # 可选
        }

    @staticmethod
    def map_building_modifier(row):
        return {
            'resource_id': row['resource_id'],
            'modifier_type': row['modifier_type'],
            'quantity': float(row['quantity'])
        }
def load_buildings_from_csv(file_path: str) -> Dict[str, Dict[str, str]]:
    buildings = {}
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            building_id = row["id"]
            buildings[building_id] = BuildingDataMapper.map_building_info(row)
    return buildings

def load_building_modifiers(file_path: str) -> Dict[str, List[Dict[str, str]]]:
    """加载建筑修正数据"""
    modifiers = {}
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            building_id = row['building_id']
            if building_id not in modifiers:
                modifiers[building_id] = []
            modifiers[building_id].append(BuildingDataMapper.map_building_modifier(row))
    return modifiers

def load_building_configs(*, buildings_file, building_modifiers_file):
    building_info_data = load_buildings_from_csv(buildings_file)
    building_modifiers_data = load_building_modifiers(building_modifiers_file)

    building_configs = {}
    for building_id, info in building_info_data.items():
        config = BuildingConfig.from_csv_row(info) # 使用 from_csv_row
        config.building_id = building_id # 确保 ID 正确
        config.modifiers = building_modifiers_data.get(building_id, [])  # 添加 modifiers
        building_configs[building_id] = config

    return building_configs