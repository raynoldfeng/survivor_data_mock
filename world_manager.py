# world_manager.py
from base_object import BaseObject
import random

class World(BaseObject):
    def __init__(self, world_config, resource_slots, actual_initial_buildings, exploration_rewards):
        super().__init__()
        self.world_config = world_config
        self.resource_slots = resource_slots
        self.actual_initial_buildings = actual_initial_buildings
        self.exploration_rewards = exploration_rewards

class WorldManager(BaseObject):
    def __init__(self, world_configs):
        super().__init__()
        self.world_configs = world_configs
        self.world_instances = {}

    def generate_worlds(self, num_worlds):
        world_ids = list(self.world_configs.keys())
        probabilities = [self.world_configs[world_id].info['occur'] for world_id in world_ids]

        for _ in range(num_worlds):
            selected_world_id = random.choices(world_ids, weights=probabilities)[0]
            world_config = self.world_configs[selected_world_id]
            resource_slots = self._generate_resource_slots(world_config)
            actual_initial_buildings = self._generate_initial_buildings(world_config)
            exploration_rewards = self._calculate_exploration_rewards(world_config)
            world = World(world_config, resource_slots, actual_initial_buildings, exploration_rewards)
            self.world_instances[world.object_id] = world

        return list(self.world_instances.values())

    def add_world_instance(self, world_instance):
        self.world_instances[world_instance.object_id] = world_instance

    def get_world_instance(self, world_id):
        return self.world_instances.get(world_id)
    
    def _generate_resource_slots(self, world_config):
        resource_slots = {}
        for res_id in world_config.info:
            if res_id.endswith("_slot"):
                base_slot = int(world_config.info[res_id])
                adjustment_key = f"{res_id[:-5]}_slot_adjustment"
                if adjustment_key in world_config.info:
                    adjustment = self._parse_adjustment(world_config.info[adjustment_key])
                    base_slot += random.randint(adjustment[0], adjustment[1])
                resource_slots[res_id[:-5]] = base_slot
        return resource_slots

    def _parse_adjustment(self, adjustment_str):
        if '~' in adjustment_str:
            parts = adjustment_str.split('~')
            return int(parts[0]), int(parts[1])
        else:
            num = int(adjustment_str)
            return num, num

    def _generate_initial_buildings(self, world_config):
        actual_buildings = []
        for structure in world_config.init_structures:
            if random.random() < structure['init_structure_probabilities_1']:
                actual_buildings.append(structure['init_structure'])
        return actual_buildings

    def _calculate_exploration_rewards(self, world_config):
        rewards = []
        for reward in world_config.explored_rewards:
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