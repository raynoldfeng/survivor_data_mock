from common import *
from basic_types.enums import *
from basic_types.world_config import WorldConfig

class WorldDataMapper:
    @staticmethod
    def map_world_info(row):
        return {
            'type': row['type'],
            'subtype': row['subtype'],
            'occur': float(row['occur']),
            'desc_id': row['desc_id'],
            'adamantium_slot': int(row['adamantium_slot']),
            'adamantium_slot_adjustment': row['adamantium_slot_adjustment'],
            'plasteel_slot': int(row['plasteel_slot']),
            'plasteel_slot_adjustment': row['plasteel_slot_adjustment'],
            'ceramite_slot': int(row['ceramite_slot']),
            'ceramite_slot_adjustment': row['ceramite_slot_adjustment'],
            'promethium_slot': int(row['promethium_slot']),
            'promethium_slot_adjustment': row['promethium_slot_adjustment'],
            'agriculture_slot': int(row['agriculture_slot']),
            'agriculture_slot_adjustment': row['agriculture_slot_adjustment'],
            'promethazine_slot': int(row['promethazine_slot']),
            'promethazine_slot_adjustment': row['promethazine_slot_adjustment'],
            'general_slot': int(row['general_slot']),
            'general_slot_adjustment': row['general_slot_adjustment'],
            'defense_slot': int(row['defense_slot']),
            'defense_slot_adjustment': row['defense_slot_adjustment']
        }

    @staticmethod
    def map_world_init_structure(row):
        return {
            'init_structure': row['init_structure'],
            'init_structure_probabilities_1': float(row['init_structure_probabilities_1']),
            'init_structure_probabilities_2': float(row['init_structure_probabilities_2'])
        }

    @staticmethod
    def map_world_explored_reward(row):
        return {
            'resource': row['resource'],
            'probability': float(row['probability']),
            'quantity_range': row['quantity_range']
        }

def load_world_info_config(file_path):
    world_info_data = {}
    mapper = WorldDataMapper()
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            world_id = row['id']
            world_info_data[world_id] = mapper.map_world_info(row)
    return world_info_data

def load_world_init_structures_config(file_path):
    world_init_structures_data = {}
    mapper = WorldDataMapper()
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            world_id = row['id']
            if world_id not in world_init_structures_data:
                world_init_structures_data[world_id] = []
            world_init_structures_data[world_id].append(mapper.map_world_init_structure(row))
    return world_init_structures_data

def load_world_explored_rewards_config(file_path):
    world_explored_rewards_data = {}
    mapper = WorldDataMapper()
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            world_id = row['id']
            if world_id not in world_explored_rewards_data:
                world_explored_rewards_data[world_id] = []
            world_explored_rewards_data[world_id].append(mapper.map_world_explored_reward(row))
    return world_explored_rewards_data

def _assemble_world_configs(world_info_data, world_init_structures_data, world_explored_rewards_data):
    world_configs = {}
    for world_id in world_info_data:
        info = world_info_data[world_id]
        init_structures = world_init_structures_data.get(world_id, [])
        explored_rewards = world_explored_rewards_data.get(world_id, [])
        config = WorldConfig(world_id, info, init_structures, explored_rewards)
        world_configs[world_id] = config
    return world_configs

def load_world_configs(*, world_info_file, world_init_structures_file, world_explored_rewards_file):
    load_functions = {
        'info': load_world_info_config,
        'init_structures': load_world_init_structures_config,
        'explored_rewards': load_world_explored_rewards_config
    }
    file_paths = {
        'info': world_info_file,
        'init_structures': world_init_structures_file,
        'explored_rewards': world_explored_rewards_file
    }

    loaded_data = {
        key: load_functions[key](file_paths[key])
        for key in load_functions
    }

    return _assemble_world_configs(loaded_data['info'], loaded_data['init_structures'], loaded_data['explored_rewards'])
