from typing import List, Dict, Optional
from base_object import BaseObject
from loader.enums import Modifier
from loader.resource import Resource
from .message_bus import MessageType, Message
import random
import uuid
from .robot import Robot

class Fleet:
    def __init__(self):
        self.morale = 100
        self.attack = 50
        self.defense = 50
        self.location = None  # 始终是坐标 (tuple)
        self.destination = None  # 始终是坐标 (tuple)
        self.travel_start_tick = 0
        self.travel_speed = 1.0
        self.travel_method = None
        self.landed_on = None  # 降落的星球 ID (如果是 None，表示没有降落)


class Player(BaseObject):
    def __init__(self, resources: Dict[str, Resource], building_config):
        super().__init__()
        self.player_id = str(uuid.uuid4())
        self.resources: Dict[str, float] = {res_id: 0.0 for res_id in resources}
        self.fleet = Fleet()
        self.avaliable_building_config = building_config
        self.characters = [{"name": "角色 1", "location": None}]
        self.explored_planets: List[str] = []
        self.planets_buildings = {}
        self.constructing_buildings = []
        self.upgrading_buildings = []
        self.action_points = 20  # 初始行动点数
        self.max_action_points = 100  # 行动点数上限
        self.action_points_recovery_per_tick = 0.1


    def get_resource_amount(self, resource_id: str) -> float:
        """获取指定资源的数量"""
        return self.resources.get(resource_id, 0.0)

    def modify_resource(self, resource_id: str, amount: float):
        """修改指定资源的数量 (可以是正数或负数)"""
        if resource_id in self.resources:
            self.resources[resource_id] += amount
            self.resources[resource_id] = max(0.0, self.resources[resource_id])

    def tick(self, tick_counter):
        """
        普通 Player 的 tick 方法，暂时返回 None。
        未来可以通过用户输入或其他方式获取操作数据。
        """
        return None


class PlayerManager():
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.players: Dict[str, Player] = {}
            cls._instance.robots: Dict[str, Robot] = {}
            cls._instance.game.player_manager = cls._instance
            cls._instance.tick_interval = 1
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_LAND, cls._instance.handle_land_request)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVEMENT_ALLOWED, cls._instance.handle_fleet_movement_allowed) #新增
        return cls._instance

    def create_player(self, resources: Dict[str, Resource], building_configs):
        player = Player(resources, building_configs)
        # 获取一个随机星球的 ID
        initial_world_id = self.game.world_manager.pick()
        # 获取该星球的坐标
        initial_world = self.game.world_manager.get_world_by_id(initial_world_id)
        if initial_world:
            self.game.log.warn(f"初始星球{initial_world.object_id}，舰队位置 {initial_world.x}, {initial_world.y}, {initial_world.z}")
            player.fleet.location = (initial_world.x, initial_world.y, initial_world.z)
        else:
            player.fleet.location = (0, 0, 0)
            self.game.log.warn("找不到初始星球，将舰队位置设置为 (0, 0, 0)")
        self.add_player(player)
        return player

    def add_player(self, player: Player):
        self.players[player.player_id] = player

    def add_robot(self, player):
        """添加 Robot"""
        self.robots[player.player_id] = Robot(player.player_id, self.game)
        return player

    def remove_player(self, player_id: str):
        if player_id in self.players:
            del self.players[player_id]

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        return self.players.get(player_id)

    def tick(self, tick_counter):
        """
        修改后的tick方法，增加tick_counter参数
        """
        if tick_counter % self.tick_interval == 0:
            # 处理所有 Player 的 tick
            for player_id, player in self.players.items():
                # 恢复行动点
                player.action_points += player.action_points_recovery_per_tick
                player.action_points = min(player.action_points, player.max_action_points)

                action_data = player.tick(
                    self.game)  # 获取 Player 的操作数据 (普通 Player 返回 None)
                if action_data:
                    self.process_action_data(action_data)

            # 处理所有 Robot 的 tick
            for robot_id, robot in self.robots.items():
                action_data = robot.tick(self.game)  # 获取 Robot 的操作数据
                if action_data:
                    self.process_action_data(action_data)
            
            # 新增:更新舰队位置(如果是slow travel)
            for player_id, player in self.players.items():
                self.update_fleet_position(player)

    def process_action_data(self, action_data):
        """处理操作数据，发送消息"""
        action = action_data['action']

        if action == 'move':
            # 获取目标星球的坐标
            target_world = self.game.world_manager.get_world_by_id(action_data["target_planet_id"])
            if target_world:
                destination = (target_world.x, target_world.y, target_world.z)
            else:
                # 如果找不到目标星球 (例如，目标是跃迁点或其他坐标)，则直接使用目标 ID (这取决于你的游戏设计)
                destination = action_data["target_planet_id"]

            # 玩家选择移动方式后，发送 PLAYER_FLEET_MOVE_REQUEST 消息
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVE_REQUEST, {
                "player_id": action_data["player_id"],
                "destination": destination,  # 目标是坐标
                "location": self.players[action_data["player_id"]].fleet.location,  # 当前位置
                "travel_method": action_data["travel_method"],  # 移动方式
            }, self)

            # 新增：如果玩家在移动过程中再次选择移动，则发送中断消息
            if self.players[action_data["player_id"]].fleet.destination is not None:
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, {
                    "player_id": action_data["player_id"],
                }, self)
        # 新增：处理降落请求
        elif action == 'land':
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_LAND, {
                "player_id": action_data["player_id"],
            }, self)

        elif action == 'build':
            self.game.message_bus.post_message(MessageType.BUILDING_REQUEST, {
                "player_id": action_data["player_id"],
                "world_id": action_data["planet_id"],
                "building_id": action_data["building_id"],
            }, self)

        elif action == 'upgrade':
            self.game.message_bus.post_message(MessageType.BUILDING_UPGRADE_REQUEST, {
                "player_id": action_data["player_id"],
                "building_id": action_data["building_id"],
            }, self)

        elif action == "select_event_option":
            self.game.message_bus.post_message(MessageType.PLAYER_SELECT_EVENT_OPTION, {
                "player_id": action_data["player_id"],
                "choice": action_data["choice"],
            }, self)

    # def fleet_move_handler(self, player_id: str, location, destination, travel_method): #移除

    def handle_fleet_movement_allowed(self, message:Message):
        """
        处理舰队移动允许的消息
        """
        player = self.get_player_by_id(message.data["player_id"])
        if not player:
            return
        
        travel_method = message.data["travel_method"]
        destination = message.data["destination"]

        # 更新fleet状态
        player.fleet.destination = destination
        player.fleet.travel_method = travel_method
        if travel_method == "subspace_jump":
            player.fleet.location = destination
            # 如果是亚空间跳跃，直接发送 FLEET_ARRIVE 消息。
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                "player_id": player.player_id,
                "location": destination, #现在统一是坐标
            }, self)
            # 亚空间跳跃后，取消降落状态
            player.fleet.landed_on = None
        elif travel_method == "slow_travel":
            player.fleet.travel_start_tick = self.game.tick_counter

    # def handle_land_request(self, player_id: str): #修改
    def handle_land_request(self, message: Message):
        """处理玩家的降落请求"""
        # player = self.get_player_by_id(player_id) #修改
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        if player.fleet.landed_on is None:  # 只有当舰队没有降落时，才能处理降落请求
            # 找到最近的星球
            nearest_world = None
            min_distance = float('inf')
            for world in self.game.world_manager.world_instances.values():
                distance = self.game.rule_manager.calculate_distance(player.fleet.location, (world.x, world.y, world.z))
                if distance < min_distance:
                    min_distance = distance
                    nearest_world = world

            # 如果最近的星球在降落范围内，则降落
            if nearest_world and min_distance <= player.fleet.travel_speed:
                player.fleet.landed_on = nearest_world.object_id
                self.game.log.info(f"Player {player.player_id} landed on world {nearest_world.object_id}")
                # 发送 PLAYER_FLEET_LAND 消息
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_LAND, {
                    "player_id": player.player_id,
                    "world_id": nearest_world.object_id,  # 新增：发送降落星球的 ID
                }, self)


    def apply_modifier(self, player_id: str, modifier: Modifier, attribute: str, quantity: float, duration: int):
        # PlayerManager 不再直接处理资源数量的修改，只负责应用 Modifier
        # 具体的资源增减由 Player.modify_resource() 处理
        pass

    def pick(self):
        if self.players:
            return random.choice(list(self.players.keys()))
        return None
    
    def update_fleet_position(self, player):
        """更新舰队位置 (如果是slow travel)"""
        if player.fleet.travel_method == "slow_travel" and isinstance(player.fleet.location, tuple):  # 舰队正在移动中
            # 获取目标坐标
            target_location = player.fleet.destination

            # 计算移动向量
            dx = target_location[0] - player.fleet.location[0]
            dy = target_location[1] - player.fleet.location[1]
            dz = target_location[2] - player.fleet.location[2]
            distance = (dx**2 + dy**2 + dz**2)**0.5

            if distance <= player.fleet.travel_speed:
                # 舰队到达目的地,发送移动消息和到达消息
                player.fleet.location = player.fleet.destination
                player.fleet.destination = None
                player.fleet.travel_method = None
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                    "player_id": player.player_id,
                    "location": player.fleet.location,  # 目标坐标
                }, self)

            else:
                # 更新舰队位置 (按比例移动)
                ratio = player.fleet.travel_speed / distance
                new_x = player.fleet.location[0] + dx * ratio
                new_y = player.fleet.location[1] + dy * ratio
                new_z = player.fleet.location[2] + dz * ratio
                # 更新位置
                player.fleet.location = (new_x, new_y, new_z)
                # 扣除资源消耗, 移动到rules_manager
                # cost = self.game.rule_manager.calculate_slow_travel_cost(distance)
                # self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                #     "target_id": player.player_id,
                #     "target_type": "Player",
                #     "resource_id": "promethium",
                #     "modifier": "REDUCE",
                #     "quantity": cost,
                #     "duration": 0,
                # }, self)