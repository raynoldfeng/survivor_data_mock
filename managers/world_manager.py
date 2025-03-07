from base_object import BaseObject
import random
from typing import Dict, Tuple, List, Optional
from .message_bus import MessageType, Message
import math

class World(BaseObject):
    def __init__(self, world_config, building_slots, actual_initial_buildings, exploration_rewards, reachable_half_extent, impenetrable_half_extent):
        super().__init__()
        self.world_config = world_config
        self.building_slots = self._init_building_slots(building_slots)
        self.actual_initial_buildings = actual_initial_buildings
        self.exploration_rewards = exploration_rewards
        self.location = (0, 0, 0)  # 中心坐标
        self.reachable_half_extent = reachable_half_extent  # 可到达半边长
        self.impenetrable_half_extent = impenetrable_half_extent  # 不可穿透半边长

    def _init_building_slots(self, building_slots: Dict[str, int]) -> Dict[str, List[Optional[str]]]:
        slots = {}
        for slot_type, count in building_slots.items():
            slots[slot_type] = [None] * count
        return slots

    def get_available_slot(self, slot_type: str) -> Optional[int]:
        if slot_type in self.building_slots:
            try:
                return self.building_slots[slot_type].index(None)
            except ValueError:
                return None
        return None

    def occupy_slot(self, slot_type: str, slot_index: int, building_id: str):
        if slot_type in self.building_slots and 0 <= slot_index < len(self.building_slots[slot_type]):
            self.building_slots[slot_type][slot_index] = building_id

    def free_slot(self, slot_type: str, slot_index: int):
        if slot_type in self.building_slots and 0 <= slot_index < len(self.building_slots[slot_type]):
            self.building_slots[slot_type][slot_index] = None

class WorldManager:
    _instance = None

    def __new__(cls, world_configs, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.locations: Dict[Tuple[int, int, int], List[str]] = {}  # 位置数据 {location: [object_id]}

            cls._instance.world_configs = world_configs
            cls._instance.world_instances: Dict[str, World] = {}
            cls._instance.game = game
            cls._instance.game.world_manager = cls._instance
            cls._instance.tick_interval = 60
        return cls._instance

    def get_objects_in_location(self, location: Tuple[int, int, int]) -> List[str]:
        """获取指定位置的所有对象 ID"""
        return self.locations.get(location, [])

    def update_object_location(self, object_id: str, old_location: Tuple[int, int, int], new_location: Tuple[int, int, int]):
        """更新对象的位置"""
        if old_location != new_location:
            if old_location in self.locations:
                if object_id in self.locations[old_location]:
                    self.locations[old_location].remove(object_id)
                if not self.locations[old_location]:
                    del self.locations[old_location]
            if new_location not in self.locations:
                self.locations[new_location] = []
            self.locations[new_location].append(object_id)

    def add_object(self, object_id: str, location: Tuple[int, int, int]):
        """添加对象"""
        if location not in self.locations:
            self.locations[location] = []
        self.locations[location].append(object_id)

    def remove_object(self, object_id: str, location: Tuple[int, int, int]):
        """移除对象"""
        if location in self.locations:
            if object_id in self.locations[location]:
                self.locations[location].remove(object_id)
            if not self.locations[location]:
                del self.locations[location]

    # --- WorldManager 原有方法 ---
    def generate_worlds(self, num_worlds: int):
        world_ids = list(self.world_configs.keys())
        probabilities = [self.world_configs[world_id].info['occur'] for world_id in world_ids]

        for _ in range(num_worlds):
            selected_world_id = random.choices(world_ids, weights=probabilities)[0]
            world_config = self.world_configs[selected_world_id]
            resource_slots = self._generate_resource_slots(world_config)
            actual_initial_buildings = self._generate_initial_buildings(world_config)
            exploration_rewards = self._calculate_exploration_rewards(world_config)

            # 随机生成星球半径 (以单元格为单位)
            reachable_half_extent = random.randint(5, 15)  # 可到达半边长
            impenetrable_half_extent = int(reachable_half_extent * random.uniform(0.6, 0.8))  # 不可穿透半边长

            world = World(world_config, resource_slots, actual_initial_buildings, exploration_rewards, reachable_half_extent, impenetrable_half_extent)

            # 分配坐标 (直接在单元格坐标空间内分配)
            max_coord = 50  # 假设世界大小为 100x100x100 个单元格
            world.location = (random.randint(-max_coord, max_coord),
                              random.randint(-max_coord, max_coord),
                              random.randint(-max_coord, max_coord))

            self.world_instances[world.object_id] = world

            # 将星球添加到 locations
            for location in self._calculate_occupied_locations(world):
                self.add_object(world.object_id, location)

        return list(self.world_instances.values())

    def _calculate_occupied_locations(self, world: World) -> List[Tuple[int, int, int]]:
        """计算星球占用的所有位置 (立方体)"""
        occupied_locations = []
        half_extent = world.impenetrable_half_extent  # 使用 impenetrable_half_extent
        for dx in range(-half_extent, half_extent + 1):
            for dy in range(-half_extent, half_extent + 1):
                for dz in range(-half_extent, half_extent + 1):
                    location = (world.location[0] + dx, world.location[1] + dy, world.location[2] + dz)
                    # 只要在以impenetrable_half_extent为半径的立方体内的cell都算作被占用
                    if (abs(location[0] - world.location[0]) <= world.impenetrable_half_extent and
                        abs(location[1] - world.location[1]) <= world.impenetrable_half_extent and
                        abs(location[2] - world.location[2]) <= world.impenetrable_half_extent):
                        occupied_locations.append(location)
        return occupied_locations

    def calculate_distance(self, location1: Tuple[int, int, int], location2: Tuple[int, int, int]) -> int:
        """计算两个位置之间的距离 (欧几里得距离, 向下取整)"""
        dx = location1[0] - location2[0]
        dy = location1[1] - location2[1]
        dz = location1[2] - location2[2]
        return int(math.sqrt(dx*dx + dy*dy + dz*dz))

    def is_world(self, object_id: str) -> bool:
        """判断给定的对象 ID 是否是星球"""
        return object_id in self.world_instances

    def get_world_at_location(self, location: Tuple[int, int, int]) -> Optional[World]:
        """获取指定位置的星球对象 (如果有)"""
        objects_in_location = self.get_objects_in_location(location)
        for object_id in objects_in_location:
            if self.is_world(object_id):
                return self.get_world_by_id(object_id)
        return None

    def add_world_instance(self, world_instance):
        self.world_instances[world_instance.object_id] = world_instance

    def get_world_by_id(self, world_id):
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
                    parts = quantity_range.split('-')
                    quantity = random.uniform(float(parts[0]), float(parts[1]))
                else:
                    quantity = float(quantity_range)
                rewards.append((reward['resource_id'], quantity))
        return rewards

    def pick(self):
        if self.world_instances:
            return random.choice(list(self.world_instances.keys()))
        return None

    def apply_modifier(self, target_id, modifier, attribute, quantity, duration):
        # World没有apply_modifier，这里留空
        pass

    def tick(self, tick_counter):
        if tick_counter % self.tick_interval == 0:
            self.update_locations() # tick时候更新
            # 遍历所有位置，检测交汇
            for location, object_ids in self.locations.items():
                if len(object_ids) > 1:
                    # 发送交汇事件
                    self.game.message_bus.post_message(MessageType.INTERSECTION_EVENT, {
                        "location": location,
                        "objects": object_ids,
                    }, self)
            pass

    def update_locations(self):
        """更新 locations 的可用性"""
        # 清空所有位置
        self.locations = {}

        # 重新添加所有星球
        for world in self.world_instances.values():
            for location in self._calculate_occupied_locations(world):
                self.add_object(world.object_id, location)
        
        # 遍历所有玩家, 把Fleet加进去
        for player_id, player in self.game.player_manager.players.items():
            fleet = player.fleet
            if fleet.location:
                self.add_object(player_id, fleet.location) # 添加舰队

    def is_location_available(self, location: Tuple[int, int, int]) -> bool:
        """判断位置是否可用(是否在不可进入的星球半径内)"""
        return not self.locations.get(location)

    def get_spawn_location(self, world: World) -> Optional[Tuple[int, int, int]]:
        """获取星球上一个可用的出生点 (单元格坐标)"""
        while True:  # 使用循环，直到找到一个可用的出生点
            # 随机选择一个轴 (x, y, 或 z)
            axis = random.choice(['x', 'y', 'z'])

            # 随机选择一个面 (+ 或 -)
            sign = random.choice([-1, 1])

            # 固定该轴向的偏移量
            if axis == 'x':
                offset_x = sign * (world.impenetrable_half_extent + 1)
                offset_y = random.randint(-world.reachable_half_extent, world.reachable_half_extent)
                offset_z = random.randint(-world.reachable_half_extent, world.reachable_half_extent)
            elif axis == 'y':
                offset_x = random.randint(-world.reachable_half_extent, world.reachable_half_extent)
                offset_y = sign * (world.impenetrable_half_extent + 1)
                offset_z = random.randint(-world.reachable_half_extent, world.reachable_half_extent)
            else:  # axis == 'z'
                offset_x = random.randint(-world.reachable_half_extent, world.reachable_half_extent)
                offset_y = random.randint(-world.reachable_half_extent, world.reachable_half_extent)
                offset_z = sign * (world.impenetrable_half_extent + 1)

            # 计算出生点坐标
            spawn_location = (
                world.location[0] + offset_x,
                world.location[1] + offset_y,
                world.location[2] + offset_z,
            )

            # 检查出生点是否可用
            if self.is_location_available(spawn_location):
                return spawn_location
