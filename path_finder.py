import heapq
import math
# 假设这些类型已经定义
from basic_types.basic_typs import *
from managers.message_bus import MessageType
import logging
from common import *

# 配置寻路日志记录器
# pathfinding_logger = logging.getLogger('pathfinding')
# pathfinding_logger.setLevel(logging.DEBUG)

# 创建文件处理器
# file_handler = logging.FileHandler('pathfinding.log')
# file_handler.setLevel(logging.DEBUG)

# 创建格式化器并添加到处理器
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# file_handler.setFormatter(formatter)

# 将处理器添加到记录器
# pathfinding_logger.addHandler(file_handler)


class OctreeNode:
    def __init__(self, min_x, max_x, min_y, max_y, min_z, max_z, depth=0):
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self.min_z = min_z
        self.max_z = max_z
        self.depth = depth
        self.children = []
        self.locations = []

    def insert(self, location: Vector3):
        if self.depth >= 5:
            self.locations.append(location)
            return

        mid_x = (self.min_x + self.max_x) / 2
        mid_y = (self.min_y + self.max_y) / 2
        mid_z = (self.min_z + self.max_z) / 2
        octant = 0
        octant |= 1 if location.x > mid_x else 0
        octant |= 2 if location.y > mid_y else 0
        octant |= 4 if location.z > mid_z else 0

        if not self.children:
            self.children = [None] * 8
            for i in range(8):
                new_min_x = self.min_x if not (i & 1) else mid_x
                new_max_x = mid_x if not (i & 1) else self.max_x
                new_min_y = self.min_y if not (i & 2) else mid_y
                new_max_y = mid_y if not (i & 2) else self.max_y
                new_min_z = self.min_z if not (i & 4) else mid_z
                new_max_z = mid_z if not (i & 4) else self.max_z
                self.children[i] = OctreeNode(new_min_x, new_max_x,
                                              new_min_y, new_max_y,
                                              new_min_z, new_max_z,
                                              self.depth + 1)
        self.children[octant].insert(location)

    def query_range(self, min_x, max_x, min_y, max_y, min_z, max_z):
        results = []
        if (self.min_x >= max_x or self.max_x <= min_x or
                self.min_y >= max_y or self.max_y <= min_y or
                self.min_z >= max_z or self.max_z <= min_z):
            return results
        if self.depth >= 5:
            return [loc for loc in self.locations if
                    min_x <= loc.x <= max_x and
                    min_y <= loc.y <= max_y and
                    min_z <= loc.z <= max_z]
        return sum((child.query_range(min_x, max_x, min_y, max_y, min_z, max_z)
                    for child in self.children if child), [])

    def remove(self, location: Vector3):
        if self.depth >= 5:
            if location in self.locations:
                self.locations.remove(location)
            return
        mid_x = (self.min_x + self.max_x) / 2
        mid_y = (self.min_y + self.max_y) / 2
        mid_z = (self.min_z + self.max_z) / 2
        octant = 0
        octant |= 1 if location.x > mid_x else 0
        octant |= 2 if location.y > mid_y else 0
        octant |= 4 if location.z > mid_z else 0
        if self.children[octant]:
            self.children[octant].remove(location)
            if not self.children[octant].children and not self.children[octant].locations:
                self.children[octant] = None


class Pathfinder:
    def __init__(self, game):
        self.game = game
        self.search_counter = 0
        self._path_cache = {}
        self._node_data = {}
        self.directions = [
            Vector3(1, 0, 0), Vector3(-1, 0, 0),
            Vector3(0, 1, 0), Vector3(0, -1, 0),
            Vector3(0, 0, 1), Vector3(0, 0, -1)
        ]

        self.max_search_steps = 1000
        self.heuristic_weight = 1.2
        self.max_straight_steps = 1
        self.max_reconstruct_steps = 500

        # 诊断系统
        self.search_counter = 0
        self._octree = None

    def find_path(self, start_location: Vector3, end_location: Vector3, speed: int = 1):
        self.search_counter += 1
        log_header = f"[Search#{self.search_counter}] {start_location}->{end_location}"
        # pathfinding_logger.debug(f"{log_header} Init")

        # 存储当前搜索的元数据
        self.current_search_meta = {
            'original_end': end_location
        }

        # 缓存检查
        cache_key = (start_location, end_location, speed)
        if cache_key in self._path_cache:
            # pathfinding_logger.debug(f"{log_header} Cache hit")
            return self._path_cache[cache_key]

        # 立即完成检查
        if self._is_goal(start_location, end_location):
            # pathfinding_logger.debug(f"{log_header} Start meets goal condition")
            return [start_location]

        # 初始化搜索
        open_heap = []
        closed_set = set()
        self._node_data.clear()

        start_h = self._heuristic_cost(start_location, end_location)
        # 起点的方向信息初始化为 None
        start_node = (start_h * self.heuristic_weight, start_location, None, 0.0, None)
        heapq.heappush(open_heap, start_node)
        self._node_data[start_location] = (*start_node, self.current_search_meta)

        steps = 0
        while open_heap and steps < self.max_search_steps:
            current_f, current_pos, parent, current_g, _ = heapq.heappop(open_heap)

            # pathfinding_logger.debug(f"{log_header} Expanding node: {current_pos}, f: {current_f}, g: {current_g}")

            # 目标检查
            if self._is_goal(current_pos, end_location):
                path = self._reconstruct_path(current_pos)
                self._path_cache[cache_key] = path
                # pathfinding_logger.debug(f"{log_header} Found path: {len(path)} steps")
                return path

            if current_pos in closed_set:
                continue
            closed_set.add(current_pos)

            # 扩展节点
            neighbors = self._get_jump_points(current_pos, end_location, speed)
            # pathfinding_logger.debug(f"{log_header} Neighbors for {current_pos}: {neighbors}")
            for neighbor in neighbors:
                if neighbor in closed_set:
                    continue

                move_cost = self._movement_cost(current_pos, neighbor)
                new_g = current_g + move_cost
                existing_node = self._node_data.get(neighbor)
                move_direction = neighbor - current_pos

                if not existing_node or new_g < existing_node[3]:
                    new_h = self._heuristic_cost(neighbor, end_location)
                    new_f = new_g + new_h * self.heuristic_weight
                    new_node = (new_f, neighbor, current_pos, new_g, move_direction)
                    heapq.heappush(open_heap, new_node)
                    self._node_data[neighbor] = (*new_node, self.current_search_meta)
                    # pathfinding_logger.debug(f"{log_header} Adding neighbor {neighbor} to open list, f: {new_f}, g: {new_g}")

            steps += 1

        # pathfinding_logger.debug(f"{log_header} No path found")
        return None

    def _get_jump_points(self, current: Vector3, end: Vector3, speed: int) -> List[Vector3]:
        jump_points = []
        for direction in self.directions:
            jump_point = self._jump(current, direction, end, speed)
            if jump_point:
                jump_points.append(jump_point)
            else:
                pass
        return jump_points

    def _jump(self, start: Vector3, direction: Vector3, end: Vector3, speed: int) -> Optional[Vector3]:
        current = start
        last_valid = None
        steps = 0
        while steps < speed:
            current += direction
            if not self._is_reachable(current):
                break
            # 检查是否到达目标
            if self._is_goal(current, end):
                return current
            # 强制邻居检查
            if self._has_forced_neighbor(current, direction):
                return current
            last_valid = current
            steps += 1

        return last_valid

    def _is_reachable(self, loc: Vector3) -> bool:
        """可达性检查"""
        return (loc.x, loc.y, loc.z) not in self.game.world_manager.get_impenetrable_grid()

    def _is_goal(self, current: Vector3, end: Vector3) -> bool:
        """增强型目标检查"""
        return current == end

    def _reconstruct_path(self, end_location: Vector3) -> List[Vector3]:
        path = []
        current_location = end_location
        max_steps = self.max_reconstruct_steps
        steps = 0

        while current_location is not None and steps < max_steps:
            # 检查节点是否存在
            if current_location not in self._node_data:
                self.game.log.error(f"Node {current_location} not found in _node_data")
                break

            # 添加当前节点到路径
            path.append(current_location)

            # 获取父节点和方向
            node = self._node_data[current_location]
            if len(node) < 5:
                self.game.log.error(f"Invalid node data for {current_location}")
                break

            parent = node[2]
            direction = node[4]

            # 起点的方向为 None，直接跳到父节点
            if direction is None:
                current_location = parent
            else:
                # 生成中间步骤
                step = current_location - direction
                while step != parent:
                    path.append(step)
                    step -= direction

                current_location = parent
            steps += 1

        # 反转路径并验证
        path.reverse()
        return path

    def _validate_path(self, path: List[Vector3], meta: dict) -> bool:
        """路径有效性验证"""
        if not path:
            return False

        last_pos = path[-1]
        end = meta['original_end']

        # 检查是否到达目标点或其相邻格子
        if last_pos != end and not self.is_contiguous(last_pos, end):
            return False

        # 检查路径中的每一步是否符合接触面移动规则
        for i in range(1, len(path)):
            if not self.is_contiguous(path[i - 1], path[i]):
                return False
        return True

    def is_contiguous(self, loc1: Vector3, loc2: Vector3) -> bool:
        """检查两个位置是否在接触面（相邻）"""
        dx = abs(loc1.x - loc2.x)
        dy = abs(loc1.y - loc2.y)
        dz = abs(loc1.z - loc2.z)
        return (dx + dy + dz) == 1

    def _movement_cost(self, a: Vector3, b: Vector3) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        dz = a.z - b.z
        cost = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        # 对目标方向的移动降低成本
        target_dir = Vector3(
            1 if b.x > a.x else -1 if b.x < a.x else 0,
            1 if b.y > a.y else -1 if b.y < a.y else 0,
            1 if b.z > a.z else -1 if b.z < a.z else 0
        )
        if dx * target_dir.x > 0:
            cost *= 0.8
        if dy * target_dir.y > 0:
            cost *= 0.8
        if dz * target_dir.z > 0:
            cost *= 0.8
        return cost

    def _on_world_added(self, world):
        if self._octree:
            for dx in range(-world.reachable_half_extent, world.reachable_half_extent + 1):
                for dy in range(-world.reachable_half_extent, world.reachable_half_extent + 1):
                    for dz in range(-world.reachable_half_extent, world.reachable_half_extent + 1):
                        loc = Vector3(world.location.x + dx, world.location.y + dy, world.location.z + dz)
                        self._octree.insert(loc)

    def _on_world_removed(self, world):
        if self._octree:
            for dx in range(-world.reachable_half_extent, world.reachable_half_extent + 1):
                for dy in range(-world.reachable_half_extent, world.reachable_half_extent + 1):
                    for dz in range(-world.reachable_half_extent, world.reachable_half_extent + 1):
                        loc = Vector3(world.location.x + dx, world.location.y + dy, world.location.z + dz)
                        self._octree.remove(loc)

    def _heuristic_cost(self, a: Vector3, b: Vector3) -> float:
        dx = abs(a.x - b.x)
        dy = abs(a.y - b.y)
        dz = abs(a.z - b.z)
        return dx + dy + dz

    def _get_orthogonal_directions(self, direction: Vector3) -> List[Vector3]:
        """获取与主方向正交的所有方向"""
        return [d for d in self.directions
                if d.dot(direction) == 0
                and d != Vector3(0, 0, 0)]

    def _has_forced_neighbor(self, pos: Vector3, direction: Vector3) -> bool:
        """三维强制邻居检测"""
        orthogonal_directions = self._get_orthogonal_directions(direction)
        for d in orthogonal_directions:
            check_pos = pos + d
            if not self._is_reachable(check_pos):
                diagonal_pos = check_pos + direction
                # 检查对角线位置是否在地图范围内
                if self._is_in_map_range(diagonal_pos) and self._is_reachable(diagonal_pos):
                    return True
        return False

    def _is_in_map_range(self, loc: Vector3) -> bool:
        # 假设地图范围由游戏世界管理器提供
        min_x, max_x, min_y, max_y, min_z, max_z = self.game.world_manager.get_map_range()
        return min_x <= loc.x <= max_x and min_y <= loc.y <= max_y and min_z <= loc.z <= max_z

    def update_octree(self):
        worlds = self.game.world_manager.world_instances.values()
        if not worlds:
            self._octree = None
            return
        min_x = min(w.location.x - w.reachable_half_extent for w in worlds)
        max_x = max(w.location.x + w.reachable_half_extent for w in worlds)
        min_y = min(w.location.y - w.reachable_half_extent for w in worlds)
        max_y = max(w.location.y + w.reachable_half_extent for w in worlds)
        min_z = min(w.location.z - w.reachable_half_extent for w in worlds)
        max_z = max(w.location.z + w.reachable_half_extent for w in worlds)
        self._octree = OctreeNode(min_x, max_x, min_y, max_y, min_z, max_z)
        for w in worlds:
            for dx in range(-w.reachable_half_extent, w.reachable_half_extent + 1):
                for dy in range(-w.reachable_half_extent, w.reachable_half_extent + 1):
                    for dz in range(-w.reachable_half_extent, w.reachable_half_extent + 1):
                        loc = Vector3(w.location.x + dx, w.location.y + dy, w.location.z + dz)
                        self._octree.insert(loc)