from base_object import BaseObject
import random
from typing import Dict, Tuple, List, Optional

class World(BaseObject):
    def __init__(self, world_config, building_slots, actual_initial_buildings, exploration_rewards):
        super().__init__()
        self.world_config = world_config
        # self.building_slots = building_slots  # 修改：不再直接存储槽位数量
        self.building_slots = self._init_building_slots(building_slots)  # 修改：初始化槽位列表
        self.actual_initial_buildings = actual_initial_buildings
        self.exploration_rewards = exploration_rewards
        self.x = 0
        self.y = 0
        self.z = 0

    def _init_building_slots(self, building_slots: Dict[str, int]) -> Dict[str, List[Optional[str]]]:
        """初始化建筑槽位列表

        Args:
            building_slots (Dict[str, int]): 包含每种槽位类型数量的字典。

        Returns:
            Dict[str, List[Optional[str]]]: 包含每种槽位类型列表的字典，
                                            列表中的每个元素代表一个槽位，
                                            值为 None 表示槽位空闲，
                                            值为建筑 ID 表示槽位已被占用。
        """
        slots = {}
        for slot_type, count in building_slots.items():
            slots[slot_type] = [None] * count  # 创建一个包含 None 的列表，长度为槽位数量
        return slots

    def get_available_slot(self, slot_type: str) -> Optional[int]:
        """获取指定类型的第一个空闲槽位的索引"""
        if slot_type in self.building_slots:
            try:
                return self.building_slots[slot_type].index(None)  # 找到第一个 None 的索引
            except ValueError:  # 如果没有找到 None (即所有槽位都已满)
                return None
        return None

    def occupy_slot(self, slot_type: str, slot_index: int, building_id: str):
        """占用指定类型的指定索引的槽位"""
        if slot_type in self.building_slots and 0 <= slot_index < len(self.building_slots[slot_type]):
            self.building_slots[slot_type][slot_index] = building_id

    def free_slot(self, slot_type: str, slot_index: int):
        """释放指定类型的指定索引的槽位"""
        if slot_type in self.building_slots and 0 <= slot_index < len(self.building_slots[slot_type]):
            self.building_slots[slot_type][slot_index] = None

class WorldManager():
    _instance = None

    def __new__(cls, world_configs, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.world_configs = world_configs
            cls._instance.world_instances: Dict[str, World] = {}
            cls._instance.game = game
            cls._instance.game.world_manager = cls._instance
            cls._instance.tick_interval = 60 # 1小时, 可以自定义
        return cls._instance

    def generate_worlds(self, num_worlds: int):
        """生成指定数量的世界，并分配坐标"""
        world_ids = list(self.world_configs.keys())
        probabilities = [self.world_configs[world_id].info['occur'] for world_id in world_ids]

        for _ in range(num_worlds):
            selected_world_id = random.choices(world_ids, weights=probabilities)[0]
            world_config = self.world_configs[selected_world_id]
            resource_slots = self._generate_resource_slots(world_config)
            actual_initial_buildings = self._generate_initial_buildings(world_config)
            exploration_rewards = self._calculate_exploration_rewards(world_config)
            world = World(world_config, resource_slots, actual_initial_buildings, exploration_rewards)

            # 分配坐标 (示例：球形分布)
            radius = 10  # 球形半径
            theta = random.uniform(0, 2 * 3.14159)  # 极角
            phi = random.uniform(-3.14159 / 2, 3.14159 / 2)  # 方位角
            world.x = int(radius * random.uniform(0, 1) *  (phi) * random.uniform(0, 1)  * (theta))
            world.y = int(radius * random.uniform(0, 1)  * (phi) * random.uniform(0, 1) * (theta))
            world.z = int(radius * random.uniform(0, 1) * (phi))

            self.world_instances[world.object_id] = world

        return list(self.world_instances.values())

    def add_world_instance(self, world_instance):
        self.world_instances[world_instance.object_id] = world_instance

    def get_world_by_id(self, world_id):  # 改为 get_world_by_id
        """根据 ID 获取 World 对象"""
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

    def pick(self):
        """随机选择一个世界"""
        if self.world_instances:
            return random.choice(list(self.world_instances.keys()))
        return None
    
    def apply_modifier(self, target_id, modifier, attribute, quantity, duration):
        #World没有apply_modifier，这里留空
        pass

    def tick(self, tick_counter):
        """
        修改后的tick方法，增加tick_counter参数, 并通过tick_interval控制频率
        """
        if tick_counter % self.tick_interval == 0:
            # 世界管理器的tick逻辑 (可以留空, 因为目前world没有特别需要tick的)
            pass