from basic_types.base_object import BaseObject
from basic_types.enums import BuildingSubTypeResource, BuildingType
from common import *
from basic_types.world import WorldInstance

class WorldManager(BaseObject):
    _instance = None

    def __new__(cls, world_configs, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.impenetrable_locations: Dict[Tuple[int, int, int], str] = {} # type: ignore

            cls._instance.world_configs = world_configs
            cls._instance.world_instances: Dict[str, WorldInstance] = {} # type: ignore
            cls._instance.game = game
            cls._instance.game.world_manager = cls._instance
            cls._instance.tick_interval = 60
        return cls._instance

    def generate_world(self, world_config, location, reachable_half_extent, impenetrable_half_extent):
        """生成单个星球 (进行碰撞检测和安全距离检查)"""
        building_slots = self._generate_resource_slots(world_config)
        exploration_rewards = self._calculate_exploration_rewards(world_config)

        temp_world = WorldInstance(
            world_config,
            building_slots,
            exploration_rewards,
            reachable_half_extent,
            impenetrable_half_extent,
            None
        )
        temp_world.location = location

        # --- 碰撞检测和安全距离检查 (改进) ---
        safe_distance_factor = 1.5  # 安全距离系数 (可调整)
        for existing_world in self.world_instances.values():
            # 计算两个星球“可到达区域”的边界之间的最小距离
            min_distance = (temp_world.reachable_half_extent + existing_world.reachable_half_extent) * safe_distance_factor
            distance_x = abs(temp_world.location[0] - existing_world.location[0])
            distance_y = abs(temp_world.location[1] - existing_world.location[1])
            distance_z = abs(temp_world.location[2] - existing_world.location[2])

            if (distance_x < min_distance and
                distance_y < min_distance and
                distance_z < min_distance):
                self.game.log.info(f"生成星球 {temp_world.world_config.world_id} 失败：与星球 {existing_world.world_config.world_id} 距离过近")
                return None  # 距离过近，返回 None

        # --- 碰撞检测 (简化) ---
        # 检查新星球的“不可穿透区域”是否与现有星球的“不可穿透区域”重叠
        for existing_world in self.world_instances.values():
            if (abs(temp_world.location[0] - existing_world.location[0]) < temp_world.impenetrable_half_extent + existing_world.impenetrable_half_extent + 1 and
                abs(temp_world.location[1] - existing_world.location[1]) < temp_world.impenetrable_half_extent + existing_world.impenetrable_half_extent + 1 and
                abs(temp_world.location[2] - existing_world.location[2]) < temp_world.impenetrable_half_extent + existing_world.impenetrable_half_extent + 1):
                self.game.log.info(f"生成星球 {temp_world.world_config.world_id} 失败：与星球 {existing_world.world_config.world_id} 发生碰撞")
                return None

        # 没有碰撞，添加到管理器
        self.world_instances[temp_world.object_id] = temp_world
        for dx in range(-temp_world.impenetrable_half_extent, temp_world.impenetrable_half_extent + 1):
            for dy in range(-temp_world.impenetrable_half_extent, temp_world.impenetrable_half_extent + 1):
                for dz in range(-temp_world.impenetrable_half_extent, temp_world.impenetrable_half_extent + 1):
                    self.impenetrable_locations[(temp_world.location[0] + dx, temp_world.location[1] + dy, temp_world.location[2] + dz)] = temp_world.object_id
        self.game.log.info(f"成功生成星球 {temp_world.world_config.world_id}，位置：{temp_world.location}")
        return temp_world
     
    def _generate_resource_slots(self, world_config):
        """生成初始的 building_slots 字典 (所有类型均为二级字典)"""
        building_slots = {
            BuildingType.RESOURCE: {},
            BuildingType.GENERAL: {},
            BuildingType.DEFENSE: {}
        }
        for res_id in world_config.info:
            if res_id.endswith("_slot"):
                base_slot = int(world_config.info[res_id])
                adjustment_key = f"{res_id[:-5]}_slot_adjustment"
                if adjustment_key in world_config.info:
                    adjustment = self._parse_adjustment(world_config.info[adjustment_key])
                    base_slot += random.randint(adjustment[0], adjustment[1])

                if res_id.startswith("general"):
                    building_slots[BuildingType.GENERAL] = base_slot
                elif res_id.startswith("defense"):
                    building_slots[BuildingType.DEFENSE] = base_slot
                else:
                    # 对于 resource 类型，添加到二级字典中
                    subtype = BuildingSubTypeResource(res_id[:-5].capitalize())  # 首字母大写，例如 "adamantium" -> "Adamantium"
                    building_slots[BuildingType.RESOURCE][subtype] = base_slot
        return building_slots

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
                rewards.append((reward['resource'], quantity))
        return rewards
    
    def _is_location_reachable(self, location: Tuple[int, int, int]) -> bool:
        """判断位置是否可到达"""
        # 遍历所有星球，检查是否在任何一个星球的不可穿透区域内
        for world in self.game.world_manager.world_instances.values():
            if location in world.impenetrable_locations:
                return False  # 在不可穿透区域内，不可到达
        return True  # 不在任何星球的不可穿透区域内，可到达
    
    def is_impenetrable(self, location: Tuple[int, int, int]) -> bool:
        """检查给定位置是否不可到达"""
        if location in self.impenetrable_locations:
            self.game.log.info(f"{location} 不可到达,与{self.impenetrable_locations[location]} 碰撞")
            return True
        else:
            return False
      
    def pick(self):
        if self.world_instances:
            return random.choice(list(self.world_instances.keys()))
        return None

    def tick(self, tick_counter):
        pass