from .imports import *
from .enums import *
from .building import Building
from .resource import Resource

class WorldDataMapper:
    @staticmethod
    def map_world_info(row):
        return {
            'type': row['type'],
            'subtype': row['subtype'],
            'occur': float(row['occur']),
            'desc_id': row['desc_id']
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
            'resource_id': row['resource_id'],
            'probability': float(row['probability']),
            'quantity_range': row['quantity_range']
        }

class WorldConfig:
    def __init__(self, world_id, info, init_structures, explored_rewards):
        self.world_id = world_id
        self.info = info
        self.init_structures = init_structures
        self.explored_rewards = explored_rewards

class World:
    def __init__(self, world_config):
        self.world_config = world_config
        self.resource_slots = self._generate_resource_slots()
        self.actual_initial_buildings = self._generate_initial_buildings()
        self.exploration_rewards = self._calculate_exploration_rewards()
        self.is_explored = False

    def _generate_resource_slots(self):
        resource_slots = {}
        for res_id in self.world_config.info:
            if res_id.endswith("_slot"):
                base_slot = int(self.world_config.info[res_id])
                adjustment_key = f"{res_id[:-5]}_slot_adjustment"
                if adjustment_key in self.world_config.info:
                    adjustment = self._parse_adjustment(self.world_config.info[adjustment_key])
                    base_slot += random.randint(adjustment[0], adjustment[1])
                resource_slots[res_id[:-5]] = base_slot
        return resource_slots

    def _parse_adjustment(self, adjustment_str):
        parts = adjustment_str.split('~')
        return int(parts[0]), int(parts[1])

    def _generate_initial_buildings(self):
        actual_buildings = []
        for structure in self.world_config.init_structures:
            if random.random() < structure['init_structure_probabilities_1']:
                actual_buildings.append(structure['init_structure'])
        return actual_buildings

    def _calculate_exploration_rewards(self):
        rewards = []
        for reward in self.world_config.explored_rewards:
            if random.random() < reward['probability']:
                quantity_range = reward['quantity_range']
                if '-' in quantity_range:
                    # 处理范围情况
                    parts = quantity_range.split('-')
                    quantity = random.uniform(float(parts[0]), float(parts[1]))
                else:
                    # 处理固定数量情况
                    quantity = float(quantity_range)
                rewards.append((reward['resource_id'], quantity))
        return rewards

    def explore_world(self):
        if self.is_explored:
            return self.exploration_rewards
        self.is_explored = True
        return self.exploration_rewards

def load_world_info(file_path):
    world_info_data = {}
    mapper = WorldDataMapper()
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            world_id = row['id']
            world_info_data[world_id] = mapper.map_world_info(row)
    return world_info_data

def load_world_init_structures(file_path):
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

def load_world_explored_rewards(file_path):
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

def _assemble_configs(world_info_data, world_init_structures_data, world_explored_rewards_data):
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
        'info': load_world_info,
        'init_structures': load_world_init_structures,
        'explored_rewards': load_world_explored_rewards
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

    return _assemble_configs(loaded_data['info'], loaded_data['init_structures'], loaded_data['explored_rewards'])

def create_world(world_config):
    return World(world_config)