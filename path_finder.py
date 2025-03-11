import heapq
from typing import Tuple, List, Dict, Optional

class Pathfinder:
    def __init__(self, game):
        self.game = game
        self._reachability_cache = {}  # 可达性缓存 (可选)
        self._node_data = {} # 存储节点数据
        self.max_search_steps = 10000  # 最大搜索步数
        self.max_search_distance = 100  # 最大搜索距离 (曼哈顿距离)
        self.heuristic_weight = 1.2  # 启发式函数权重

    def find_path(self, start_location: Tuple[int, int, int], end_location: Tuple[int, int, int], target_type: str = "coordinate", target_world_id: Optional[str] = None) -> Optional[List[Tuple[int, int, int]]]:
        """
        使用 A* 算法寻找从 start_location 到 end_location 的最短路径。

        Args:
            start_location: 起始坐标 (x, y, z)。
            end_location: 目标坐标 (x, y, z)。
            target_type: 目标类型，"coordinate" 表示普通坐标，"world" 表示星球。
            target_world_id: 如果 target_type 是 "world"，则此参数是目标星球的 ID。

        Returns:
            如果找到路径，返回路径 (坐标列表)。
            如果找不到路径，返回 None。
            如果已经在目标位置, 返回 []
        """

        # 1. 检查起点和终点是否相同 (或足够接近)
        if start_location == end_location:
            return []  # 直接返回空列表
        
        #判断是否已经在星球表面
        if target_type == "world":
            world = self.game.world_manager.get_world_by_id(target_world_id)
            if world:
                if world.is_on_surface(start_location):
                    return []  # 返回空列表

        open_list = []  # 开放列表 (待探索的节点), 使用 heapq
        closed_list = set()  # 关闭列表 (已探索过的节点)
        self._node_data = {} # 存储节点数据

        # 节点数据结构: (f_cost, location, parent, g_cost)
        start_node = (self._heuristic_cost(start_location, end_location) * self.heuristic_weight, start_location, None, 0)
        heapq.heappush(open_list, start_node)
        self._node_data[start_location] = start_node

        steps = 0  # 记录搜索步数
        while open_list:
            f_cost, current_location, parent, g_cost = heapq.heappop(open_list)

            if target_type == "coordinate" and current_location == end_location:
                return self._reconstruct_path(current_location) # 返回路径
            # 增加对星球表面的判断
            elif target_type == "world":
                world =  self.game.world_manager.get_world_by_id(target_world_id)
                if world and world.is_on_surface(current_location):
                    return self._reconstruct_path(current_location) # 返回路径

            if current_location in closed_list:
                continue  # 如果已经在关闭列表中，跳过 (惰性删除)
            closed_list.add(current_location)

            # 限制搜索步数
            steps += 1
            if steps > self.max_search_steps:
                print("达到最大搜索步数，寻路失败")
                return None # 返回 None

            # 限制搜索距离
            if g_cost + self._heuristic_cost(current_location, end_location) > self.max_search_distance:
                continue

            # 遍历相邻节点
            for neighbor_location in self._get_neighbors(current_location):
                if neighbor_location in closed_list:
                    continue  # 跳过已探索过的节点

                new_g_cost = g_cost + 1  # 假设每移动一步的代价为 1

                if neighbor_location not in self._node_data:
                    # neighbor_location 不在 open_list 中，添加到 open_list
                    new_h_cost = self._heuristic_cost(neighbor_location, end_location)
                    new_f_cost = new_g_cost + new_h_cost * self.heuristic_weight
                    new_node = (new_f_cost, neighbor_location, current_location, new_g_cost)
                    heapq.heappush(open_list, new_node)
                    self._node_data[neighbor_location] = new_node
                elif new_g_cost < self._node_data[neighbor_location][3]:
                    # neighbor_location 已在 open_list 中，但新的 g_cost 更小，更新节点信息
                    new_h_cost = self._heuristic_cost(neighbor_location, end_location)
                    new_f_cost = new_g_cost + new_h_cost * self.heuristic_weight
                    updated_node = (new_f_cost, neighbor_location, current_location, new_g_cost)
                    heapq.heappush(open_list, updated_node)  # 添加新节点 (惰性删除)
                    self._node_data[neighbor_location] = updated_node # 更新节点数据

        # 循环结束，未找到路径
        return None

    def _get_neighbors(self, location: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
        """获取指定位置的相邻可通行位置"""
        neighbors = []
        x, y, z = location
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue  # 跳过自身
                    neighbor_location = (x + dx, y + dy, z + dz)
                    if self._is_location_reachable(neighbor_location):
                        neighbors.append(neighbor_location)
        return neighbors

    def _is_location_reachable(self, location: Tuple[int, int, int]) -> bool:
        """判断位置是否可到达"""
        # 使用 WorldManager 的 is_cell_available 方法
        return self.game.world_manager._is_location_reachable(location)

    def _heuristic_cost(self, location1: Tuple[int, int, int], location2: Tuple[int, int, int]) -> int:
        """计算两个位置之间的启发式代价 (曼哈顿距离)"""
        return abs(location1[0] - location2[0]) + abs(location1[1] - location2[1]) + abs(location1[2] - location2[2])

    def _reconstruct_path(self, end_location: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
        """从终点回溯，构建路径"""
        path = []
        current_location = end_location
        while current_location is not None:
            path.append(current_location)
            current_location = self._node_data[current_location][2]  # 获取父节点
        path.reverse()  # 反转列表，得到从起点到终点的路径
        return path

    def __init__(self, game):
        self.game = game
        self._reachability_cache = {}  # 可达性缓存 (可选)
        self._node_data = {} # 存储节点数据
        self.max_search_steps = 10000  # 最大搜索步数
        self.max_search_distance = 100  # 最大搜索距离 (曼哈顿距离)
        self.heuristic_weight = 1.2  # 启发式函数权重

    def find_path(self, start_location: Tuple[int, int, int], end_location: Tuple[int, int, int], target_type: str = "coordinate", target_world_id: Optional[str] = None) -> Optional[List[Tuple[int, int, int]]]:
        """
        使用 A* 算法寻找从 start_location 到 end_location 的最短路径。

        Args:
            start_location: 起始坐标 (x, y, z)。
            end_location: 目标坐标 (x, y, z)。
            target_type: 目标类型，"coordinate" 表示普通坐标，"world" 表示星球。
            target_world_id: 如果 target_type 是 "world"，则此参数是目标星球的 ID。

        Returns:
            如果找到路径，返回路径 (坐标列表)。
            如果找不到路径，返回 None。
            如果已经在目标位置, 返回 []
        """

        # 1. 检查起点和终点是否相同 (或足够接近)
        if start_location == end_location:
            return []  # 直接返回空列表
        
        #判断是否已经在星球表面
        if target_type == "world":
            world = self.game.world_manager.get_world_by_id(target_world_id)
            if world:
                if world.is_on_surface(start_location):
                    return []  # 返回空列表

        open_list = []  # 开放列表 (待探索的节点), 使用 heapq
        closed_list = set()  # 关闭列表 (已探索过的节点)
        self._node_data = {} # 存储节点数据

        # 节点数据结构: (f_cost, location, parent, g_cost)
        start_node = (self._heuristic_cost(start_location, end_location) * self.heuristic_weight, start_location, None, 0)
        heapq.heappush(open_list, start_node)
        self._node_data[start_location] = start_node

        steps = 0  # 记录搜索步数
        while open_list:
            f_cost, current_location, parent, g_cost = heapq.heappop(open_list)

            if target_type == "coordinate" and current_location == end_location:
                return self._reconstruct_path(current_location) # 返回路径
            # 增加对星球表面的判断
            elif target_type == "world":
                world =  self.game.world_manager.get_world_by_id(target_world_id)
                if world and world.is_on_surface(current_location):
                    return self._reconstruct_path(current_location) # 返回路径

            if current_location in closed_list:
                continue  # 如果已经在关闭列表中，跳过 (惰性删除)
            closed_list.add(current_location)

            # 限制搜索步数
            steps += 1
            if steps > self.max_search_steps:
                print("达到最大搜索步数，寻路失败")
                return None # 返回 None

            # 限制搜索距离
            if g_cost + self._heuristic_cost(current_location, end_location) > self.max_search_distance:
                continue

            # 遍历相邻节点
            for neighbor_location in self._get_neighbors(current_location):
                if neighbor_location in closed_list:
                    continue  # 跳过已探索过的节点

                new_g_cost = g_cost + 1  # 假设每移动一步的代价为 1

                if neighbor_location not in self._node_data:
                    # neighbor_location 不在 open_list 中，添加到 open_list
                    new_h_cost = self._heuristic_cost(neighbor_location, end_location)
                    new_f_cost = new_g_cost + new_h_cost * self.heuristic_weight
                    new_node = (new_f_cost, neighbor_location, current_location, new_g_cost)
                    heapq.heappush(open_list, new_node)
                    self._node_data[neighbor_location] = new_node
                elif new_g_cost < self._node_data[neighbor_location][3]:
                    # neighbor_location 已在 open_list 中，但新的 g_cost 更小，更新节点信息
                    new_h_cost = self._heuristic_cost(neighbor_location, end_location)
                    new_f_cost = new_g_cost + new_h_cost * self.heuristic_weight
                    updated_node = (new_f_cost, neighbor_location, current_location, new_g_cost)
                    heapq.heappush(open_list, updated_node)  # 添加新节点 (惰性删除)
                    self._node_data[neighbor_location] = updated_node # 更新节点数据

        # 循环结束，未找到路径
        return None

    def _get_neighbors(self, location: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
        """获取指定位置的相邻可通行位置"""
        neighbors = []
        x, y, z = location
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue  # 跳过自身
                    neighbor_location = (x + dx, y + dy, z + dz)
                    if self._is_location_reachable(neighbor_location):
                        neighbors.append(neighbor_location)
        return neighbors

    def _is_location_reachable(self, location: Tuple[int, int, int]) -> bool:
        """判断位置是否可到达"""
        # 使用 WorldManager 的 is_cell_available 方法
        return self.game.world_manager._is_location_reachable(location)

    def _heuristic_cost(self, location1: Tuple[int, int, int], location2: Tuple[int, int, int]) -> int:
        """计算两个位置之间的启发式代价 (曼哈顿距离)"""
        return abs(location1[0] - location2[0]) + abs(location1[1] - location2[1]) + abs(location1[2] - location2[2])

    def _reconstruct_path(self, end_location: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
        """从终点回溯，构建路径"""
        path = []
        current_location = end_location
        while current_location is not None:
            path.append(current_location)
            current_location = self._node_data[current_location][2]  # 获取父节点
        path.reverse()  # 反转列表，得到从起点到终点的路径
        return path