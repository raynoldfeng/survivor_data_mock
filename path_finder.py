import heapq
from typing import Tuple, List, Dict, Optional
from basic_types.basic_typs import *
from managers.message_bus import MessageType

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
        self._octree = None
        self._path_cache = {}
        self._node_data = {}
        self.current_search_meta = {}  # 存储当前搜索的元数据
        
        # 三维运动方向（优化后的26方向）
        self.directions = [
            Vector3(1,0,0), Vector3(-1,0,0), 
            Vector3(0,1,0), Vector3(0,-1,0), 
            Vector3(0,0,1), Vector3(0,0,-1),
            Vector3(1,1,0), Vector3(1,-1,0), 
            Vector3(-1,1,0), Vector3(-1,-1,0),
            Vector3(1,0,1), Vector3(1,0,-1), 
            Vector3(-1,0,1), Vector3(-1,0,-1),
            Vector3(0,1,1), Vector3(0,1,-1), 
            Vector3(0,-1,1), Vector3(0,-1,-1),
            Vector3(1,1,1), Vector3(1,1,-1), 
            Vector3(1,-1,1), Vector3(1,-1,-1),
            Vector3(-1,1,1), Vector3(-1,1,-1), 
            Vector3(-1,-1,1), Vector3(-1,-1,-1)
        ]
        
        # 性能参数
        self.max_search_steps = 1000
        self.heuristic_weight = 1.2
        self.max_straight_steps = 25
        self.max_reconstruct_steps = 500
        
        # 诊断系统
        self.search_counter = 0
        
        self.game.message_bus.subscribe(MessageType.WORLD_ADDED, self._on_world_added)
        self.game.message_bus.subscribe(MessageType.WORLD_REMOVED, self._on_world_removed)

    def find_path(self, start_location: Vector3, end_location: Vector3, 
                 target_type: str = "coordinate", target_world_id: Optional[str] = None) -> Optional[List[Vector3]]:
        self.search_counter += 1
        log_header = f"[Search#{self.search_counter}] {start_location}->{end_location}"
        self.game.log.debug(f"{log_header} Init")
        
        # 存储当前搜索的元数据
        self.current_search_meta = {
            'target_type': target_type,
            'target_world_id': target_world_id,
            'original_end': end_location
        }
        
        # 缓存检查
        cache_key = (start_location, end_location, target_type, target_world_id)
        if cache_key in self._path_cache:
            self.game.log.debug(f"{log_header} Cache hit")
            return self._path_cache[cache_key]
        
        # 立即完成检查
        if self._is_immediate_goal(start_location, end_location, target_type, target_world_id):
            self.game.log.debug(f"{log_header} Start meets goal condition")
            return [start_location]
        
        # 初始化搜索
        open_heap = []
        closed_set = set()
        self._node_data.clear()
        
        start_h = self._heuristic_cost(start_location, end_location)
        start_node = (start_h * self.heuristic_weight, start_location, None, 0.0)
        heapq.heappush(open_heap, start_node)
        self._node_data[start_location] = (*start_node, self.current_search_meta)
        
        steps = 0
        while open_heap and steps < self.max_search_steps:
            current_f, current_pos, parent, current_g = heapq.heappop(open_heap)
            
            # 目标检查
            if self._is_goal(current_pos, end_location, target_type, target_world_id):
                path = self._reconstruct_path(current_pos)
                self._path_cache[cache_key] = path
                self.game.log.debug(f"{log_header} Found path: {len(path)} steps")
                return path
            
            if current_pos in closed_set:
                continue
            closed_set.add(current_pos)
            
            # 扩展节点
            for neighbor in self._get_jump_points(current_pos, end_location):
                if neighbor in closed_set:
                    continue
                
                move_cost = self._movement_cost(current_pos, neighbor)
                new_g = current_g + move_cost
                existing_node = self._node_data.get(neighbor)
                
                if not existing_node or new_g < existing_node[3]:
                    new_h = self._heuristic_cost(neighbor, end_location)
                    new_f = new_g + new_h * self.heuristic_weight
                    new_node = (new_f, neighbor, current_pos, new_g)
                    heapq.heappush(open_heap, new_node)
                    self._node_data[neighbor] = (*new_node, self.current_search_meta)
            
            steps += 1
        
        self.game.log.debug(f"{log_header} No path found")
        return None

    def _is_immediate_goal(self, pos: Vector3, end: Vector3, target_type: str, world_id: Optional[str]) -> bool:
        """立即判断是否满足目标条件"""
        if target_type == "coordinate":
            return pos == end
        elif target_type == "world":
            world = self.game.world_manager.get_world_by_id(world_id)
            return world and world.is_on_surface(pos)
        return False

    def _heuristic_cost(self, a: Vector3, b: Vector3) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        dz = a.z - b.z
        return math.sqrt(dx**2 + dy**2 + dz**2)

    def _get_jump_points(self, current: Vector3, end: Vector3) -> List[Vector3]:
        jump_points = []
        for direction in self.directions:
            jump_point = self._jump(current, direction, end)
            if jump_point:
                jump_points.append(jump_point)
        return jump_points

    def _jump(self, start: Vector3, direction: Vector3, end: Vector3) -> Optional[Vector3]:
        current = start + direction
        last_valid = None
        steps = 0
        
        while steps < self.max_straight_steps:
            if not self._is_reachable(current):
                break
            
            # 检查是否到达目标
            if self._is_goal(current, end, 
                            self.current_search_meta['target_type'],
                            self.current_search_meta['target_world_id']):
                return current
            
            # 强制邻居检查
            if self._has_forced_neighbor(current, direction):
                return current
            
            # 对角线跳跃检查
            if any(self._check_diagonal(current, direction, d) for d in self._get_orthogonal_directions(direction)):
                return current
            
            last_valid = current
            current += direction
            steps += 1
        
        return last_valid

    def _check_diagonal(self, pos: Vector3, main_dir: Vector3, ortho_dir: Vector3) -> bool:
        """检查对角线跳跃可能性"""
        check_pos = pos + ortho_dir
        jump_pos = check_pos + main_dir
        return (not self._is_reachable(check_pos)) and self._is_reachable(jump_pos)

    def _get_orthogonal_directions(self, direction: Vector3) -> List[Vector3]:
        """获取与主方向正交的所有方向"""
        return [d for d in self.directions 
               if d.dot(direction) == 0 
               and d != Vector3(0,0,0)]

    def _has_forced_neighbor(self, pos: Vector3, direction: Vector3) -> bool:
        """三维强制邻居检测"""
        for d in self._get_orthogonal_directions(direction):
            check_pos = pos + d
            if not self._is_reachable(check_pos):
                diagonal_pos = check_pos + direction
                if self._is_reachable(diagonal_pos):
                    return True
        return False

    def _is_reachable(self, loc: Vector3) -> bool:
        """可达性检查"""
        return (loc.x, loc.y, loc.z) not in self.game.world_manager.get_impenetrable_grid()

    def _is_goal(self, current: Vector3, end: Vector3, target_type: str, world_id: Optional[str]) -> bool:
        """增强型目标检查"""
        if target_type == "coordinate":
            return current.distance(end) < 1.0
        elif target_type == "world":
            world = self.game.world_manager.get_world_by_id(world_id)
            return world and world.is_on_surface(current)
        return False

    def _reconstruct_path(self, end_location: Vector3) -> List[Vector3]:
        path = []
        current_location = end_location
        max_steps = 1000
        steps = 0
        target_world_id = None
        
        # 从node_data中获取目标信息
        if end_location in self._node_data:
            node = self._node_data[end_location]
            if len(node) >= 5:
                _, _, _, _, metadata = node
                target_world_id = metadata.get('target_world_id')
        
        self.game.log.info(f"Reconstructing path for target_world_id: {target_world_id}")
        
        while current_location is not None and steps < max_steps:
            # 处理目标为WORLD的特殊情况
            if target_world_id:
                world = self.game.world_manager.get_world_by_id(target_world_id)
                if world and world.is_on_surface(current_location):
                    self.game.log.info(f"Already on target world {target_world_id}, adding to path")
                    path.append(current_location)
            
            # 检查节点是否存在
            if current_location not in self._node_data:
                self.game.log.error(f"Node {current_location} not found in _node_data")
                break
            
            # 添加当前节点到路径
            path.append(current_location)
            
            # 获取父节点
            node = self._node_data[current_location]
            if len(node) < 3:
                self.game.log.error(f"Invalid node data for {current_location}")
                break
            
            parent = node[2]  # 正确索引为2（第三个元素）
            
            # 检查循环引用
            if parent == current_location:
                self.game.log.error(f"Cycle detected at {current_location}")
                break
            
            current_location = parent
            steps += 1
        
        # 反转路径并验证
        path.reverse()
        if target_world_id:
            world = self.game.world_manager.get_world_by_id(target_world_id)
            if world and not any(world.is_on_surface(loc) for loc in path):
                self.game.log.error("Path does not reach target world")
                return []
        return path

    def _validate_path(self, path: List[Vector3], meta: dict) -> bool:
        """路径有效性验证"""
        if not path:
            return False
            
        last_pos = path[-1]
        if meta['target_type'] == "coordinate":
            return last_pos.distance(meta['original_end']) < 1.0
        elif meta['target_type'] == "world":
            world = self.game.world_manager.get_world_by_id(meta['target_world_id'])
            return world and world.is_on_surface(last_pos)
        return False

    def _movement_cost(self, a: Vector3, b: Vector3) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        dz = a.z - b.z
        cost = math.sqrt(dx**2 + dy**2 + dz**2)
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