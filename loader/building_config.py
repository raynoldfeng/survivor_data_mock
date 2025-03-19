from basic_types.modifier import ModifierConfig
from basic_types.resource import Resource
from common import *
from basic_types.building_config import BuildingConfig
from basic_types.enums import *

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
        modifier_config =  ModifierConfig(
            data_type = row['resource'],
            modifier_type = ModifierType(row['modifier']),
            quantity = float(row['quantity']),
            target_type = ObjectType.PLAYER,
            duration = 0,
            delay = 0,
        )
        return modifier_config
    
def load_buildings_from_csv(file_path: str) -> Dict[str, Dict[str, str]]:
    buildings = {}
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            config_id = row["id"]
            buildings[config_id] = BuildingDataMapper.map_building_info(row)
    return buildings

def load_building_modifier_configs(file_path: str) -> Dict[str, List[Dict[str, str]]]:
    """加载建筑修正数据"""
    configs = {}
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            config_id = row['building_id']
            if config_id not in configs:
                configs[config_id] = []
            configs[config_id].append(BuildingDataMapper.map_building_modifier(row))
    return configs

def load_building_configs(*, buildings_file, building_modifiers_file):
    building_info_data = load_buildings_from_csv(buildings_file)
    building_modifiers_config_data = load_building_modifier_configs(building_modifiers_file)

    building_configs = {}
    for config_id, info in building_info_data.items():
        config = BuildingConfig.from_csv_row(info) # 使用 from_csv_row
        config.config_id = config_id # 确保 ID 正确
        config.modifier_configs = building_modifiers_config_data.get(config_id, [])
        building_configs[config_id] = config

    return building_configs