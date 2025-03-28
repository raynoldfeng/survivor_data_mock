from common import *
from basic_types.enums import *
from .basic_typs import Vector3
from .base_object import BaseObject

class WorldInstance(BaseObject):
    def __init__(self, world_config, building_slots, exploration_rewards, reachable_half_extent, impenetrable_half_extent, player_id):
        super().__init__()
        self.type = ObjectType.WORLD
        self.world_config = world_config
        self.building_slots = building_slots 
        self.exploration_rewards = exploration_rewards
        self.location :Vector3 = Vector3(0,0,0)
        self.reachable_half_extent = reachable_half_extent  # 可到达半边长
        self.impenetrable_half_extent = impenetrable_half_extent  # 不可穿透半边长
        self.impenetrable_locations: Set[Vector3] = self._calculate_impenetrable_locations()  # 不可穿透区域的坐标
        self.docked_fleets: Dict[str, Vector3] = {}  # 停靠的舰队 {player_id: fleet_location}
        self.owner = player_id

    def _parse_adjustment(self, adjustment_str):
        if '~' in adjustment_str:
            parts = adjustment_str.split('~')
            return int(parts[0]), int(parts[1])
        else:
            num = int(adjustment_str)
            return num, num

    def is_on_surface(self, location: Vector3) -> bool:
        """判断给定坐标是否在该星球表面"""
        dx = abs(location.x - self.location.x)
        dy = abs(location.y - self.location.y)
        dz = abs(location.z - self.location.z)

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

    def check_collision(self, location: Vector3) -> bool:
        """检查给定坐标是否与星球发生碰撞（即坐标位于星球表面, 或不可穿透区域）"""
        dx = abs(location.x - self.location.x)
        dy = abs(location.y - self.location.y)
        dz = abs(location.z - self.location.z)
        return (
            dx <= self.reachable_half_extent and
            dy <= self.reachable_half_extent and
            dz <= self.reachable_half_extent
        )

    def _calculate_impenetrable_locations(self) -> Set[Vector3]:
        """计算星球不可穿透区域的所有坐标"""
        locations = set()
        for dx in range(-self.impenetrable_half_extent, self.impenetrable_half_extent + 1):
            for dy in range(-self.impenetrable_half_extent, self.impenetrable_half_extent + 1):
                for dz in range(-self.impenetrable_half_extent, self.impenetrable_half_extent + 1):
                    locations.add(Vector3(self.location.x + dx, self.location.y + dy, self.location.z + dz))
        return locations

    def get_spawn_location(self) -> Vector3:
        """获取星球上一个可用的出生点 (单元格坐标)"""
        while True:  # 使用循环，直到找到一个可用的出生点
            # 随机选择一个轴 (x, y, 或 z)
            axis = random.choice(['x', 'y', 'z'])

            # 随机选择一个面 (+ 或 -)
            sign = random.choice([-1, 1])

            # 固定该轴向的偏移量
            if axis == 'x':
                offset_x = sign * (self.impenetrable_half_extent + 1)
                offset_y = random.randint(-self.reachable_half_extent, self.reachable_half_extent)
                offset_z = random.randint(-self.reachable_half_extent, self.reachable_half_extent)
            elif axis == 'y':
                offset_x = random.randint(-self.reachable_half_extent, self.reachable_half_extent)
                offset_y = sign * (self.impenetrable_half_extent + 1)
                offset_z = random.randint(-self.reachable_half_extent, self.reachable_half_extent)
            else:  # axis == 'z'
                offset_x = random.randint(-self.reachable_half_extent, self.reachable_half_extent)
                offset_y = random.randint(-self.reachable_half_extent, self.reachable_half_extent)
                offset_z = sign * (self.impenetrable_half_extent + 1)

            # 计算出生点坐标
            spawn_location = Vector3(
                self.location.x + offset_x,
                self.location.y + offset_y,
                self.location.z + offset_z,
            )
            return spawn_location
        