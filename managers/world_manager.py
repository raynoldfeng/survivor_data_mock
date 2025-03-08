from base_object import BaseObject
import random
from typing import Dict, Tuple, List, Optional
from .message_bus import MessageType, Message
import math

class World(BaseObject):
    def __init__(self, world_config, building_slots, exploration_rewards, reachable_half_extent, impenetrable_half_extent):
        super().__init__()
        self.world_config = world_config
        self.building_slots = building_slots  # 直接使用传入的 building_slots (已经是二级字典)
        self.exploration_rewards = exploration_rewards
        self.location = (0, 0, 0)  # 中心坐标
        self.reachable_half_extent = reachable_half_extent  # 可到达半边长
        self.impenetrable_half_extent = impenetrable_half_extent  # 不可穿透半边长
        self.docked_fleets: Dict[str, Tuple[int, int, int]] = {}  # 新增：停靠的舰队 {player_id: fleet_location}


    def _parse_adjustment(self, adjustment_str):
        if '~' in adjustment_str:
            parts = adjustment_str.split('~')
            return int(parts[0]), int(parts[1])
        else:
            num = int(adjustment_str)
            return num, num

    def is_on_surface(self, location: Tuple[int, int, int]) -> bool:
        """判断给定坐标是否在该星球表面"""
        dx = abs(location[0] - self.location[0])
        dy = abs(location[1] - self.location[1])
        dz = abs(location[2] - self.location[2])

        return (
            dx <= self.reachable_half_extent and
            dy <= self.reachable_half_extent and
            dz <= self.reachable_half_extent and
            (
                dx == self.impenetrable_half_extent + 1 or
                dy == self.impenetrable_half_extent + 1 or
                dz == self.impenetrable_half_extent + 1
            )
        )

    def check_collision(self, location: Tuple[int, int, int]) -> bool:
        """检查给定坐标是否与星球发生碰撞（即坐标位于星球表面）"""
        # 与 is_on_surface() 的逻辑相同, 但包含不可通行区域
        dx = abs(location[0] - self.location[0])
        dy = abs(location[1] - self.location[1])
        dz = abs(location[2] - self.location[2])
        return (
            dx <= self.reachable_half_extent and
            dy <= self.reachable_half_extent and
            dz <= self.reachable_half_extent
        )

    def calculate_distance_to_center(self, location: Tuple[int, int, int]) -> float:
        """计算给定位置到星球中心的距离（欧几里得距离）"""
        dx = location[0] - self.location[0]
        dy = location[1] - self.location[1]
        dz = location[2] - self.location[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)

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

    def generate(self, location, world_config, building_slots, exploration_rewards, reachable_half_extent, impenetrable_half_extent) -> World:
        world = World(world_config, building_slots, exploration_rewards, reachable_half_extent, impenetrable_half_extent)
        world.location= location
        self.world_instances[world.object_id] = world
        return world

    def _generate_resource_slots(self, world_config):
        """生成初始的 building_slots 字典 (所有类型均为二级字典)"""
        building_slots = {
            "resource": {},
            "general": {},  # 改为二级字典
            "defense": {}   # 改为二级字典
        }
        for res_id in world_config.info:
            if res_id.endswith("_slot"):
                base_slot = int(world_config.info[res_id])
                adjustment_key = f"{res_id[:-5]}_slot_adjustment"
                if adjustment_key in world_config.info:
                    adjustment = self._parse_adjustment(world_config.info[adjustment_key])
                    base_slot += random.randint(adjustment[0], adjustment[1])

                if res_id.startswith("general"):
                    building_slots["general"]["general"] = base_slot  # 添加到二级字典
                elif res_id.startswith("defense"):
                    building_slots["defense"]["defense"] = base_slot  # 添加到二级字典
                else:
                    # 对于 resource 类型，添加到二级字典中
                    subtype = res_id[:-5].capitalize()  # 首字母大写，例如 "adamantium" -> "Adamantium"
                    building_slots["resource"][subtype] = base_slot
        return building_slots

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

    def add_world_instance(self, world_instance):
        self.world_instances[world_instance.object_id] = world_instance

    def get_world_by_id(self, world_id):
        return self.world_instances.get(world_id)

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

    def tick(self, tick_counter):
        pass

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