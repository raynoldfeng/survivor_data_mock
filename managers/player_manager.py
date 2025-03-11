from typing import List, Dict, Optional, Tuple
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
        self.path = []
        self.travel_start_round = 0
        self.travel_speed = 1.0 # 现在速度的单位是 cell/tick
        self.travel_method = None
        self.landed_on = None
        self.location = (0,0,0) # 单元格坐标


    def set_path(self, path: List[Tuple[int, int, int]]):
        """设置路径"""
        self.path = path

    def set_travel_method(self, travel_method):
        self.travel_method = travel_method

    def move_to_next_cell(self):
        """移动到路径的下一个单元格 (或朝 dest 移动)"""
        if self.path:
            self.path.pop(0)  # 移除当前单元格


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
        self.action_points = 5
        self.max_action_points = 20
        self.action_points_recovery_per_minute = 0.1

    def get_resource_amount(self, resource_id: str) -> float:
        """获取指定资源的数量"""
        return self.resources.get(resource_id, 0.0)

    def modify_resource(self, resource_id: str, amount: float):
        """修改指定资源的数量 (可以是正数或负数)"""
        if resource_id in self.resources:
            self.resources[resource_id] += amount
            self.resources[resource_id] = max(0.0, self.resources[resource_id])

    def tick(self, game):
        """
        普通 Player 的 tick 方法，暂时返回 None。
        未来可以通过用户输入或其他方式获取操作数据。
        """
        return None

class PlayerManager:
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.players: Dict[str, Player] = {}
            cls._instance.robots: Dict[str, Robot] = {}
            cls._instance.game.player_manager = cls._instance
            cls._instance.tick_interval = 1
            # 新增：存储每个玩家舰队的位置
            cls._instance.fleet_locations: Dict[Tuple[int, int, int], List[str]] = {}
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_RESOURCE_CHANGED, cls._instance.handle_player_resource_changed)
        return cls._instance

    def create_player(self, resources: Dict[str, Resource], building_configs):
        player = Player(resources, building_configs)
        initial_world_id = self.game.world_manager.pick()
        initial_world = self.game.world_manager.get_world_by_id(initial_world_id)
        if initial_world:
            spawn_location = initial_world.get_spawn_location()
            if spawn_location:
                self.game.log.warn(f"初始星球{initial_world.object_id}，舰队位置 {spawn_location}")
                player.fleet.location = spawn_location
                # 新增：将玩家的初始舰队位置添加到 fleet_locations
                self.fleet_locations[player.fleet.location] = [player.player_id]
            else:
                self.game.log.warn(f"无法为星球 {initial_world.object_id} 找到可到达的出生点，将舰队位置设置为 (0, 0, 0)")
                player.fleet.location = (0, 0, 0)
        else:
            self.game.log.warn("找不到初始星球，将舰队位置设置为 (0, 0, 0)")
            player.fleet.location = (0, 0, 0)
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
            # 新增：从 fleet_locations 中移除玩家舰队的位置
            player = self.players[player_id]
            if player.fleet.location in self.fleet_locations:
                self.fleet_locations[player.fleet.location].remove(player_id)
                if not self.fleet_locations[player.fleet.location]:
                    del self.fleet_locations[player.fleet.location]
            del self.players[player_id]

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        return self.players.get(player_id)
    
    def update_fleet_location(self, player_id: str, old_location: Tuple[int, int, int], new_location: Tuple[int, int, int]):
        """更新玩家舰队的位置"""
        # 从旧位置移除
        if old_location in self.fleet_locations:
            if player_id in self.fleet_locations[old_location]:
                self.fleet_locations[old_location].remove(player_id)
            if not self.fleet_locations[old_location]:
                del self.fleet_locations[old_location]
        # 添加到新位置
        if new_location not in self.fleet_locations:
            self.fleet_locations[new_location] = []
        self.fleet_locations[new_location].append(player_id)

    def tick(self, tick_counter):
        if tick_counter % self.tick_interval == 0:
            for player_id, player in self.players.items():
                player.action_points += player.action_points_recovery_per_minute
                player.action_points = min(player.action_points, player.max_action_points)

                actions = player.tick(self.game)
                if actions is not None:
                    for action in actions:
                        self.process_action_data(action)

            for robot_id, robot in self.robots.items():
                actions = robot.tick(self.game)
                if actions is not None:
                    for action in actions:
                        self.process_action_data(action)

    def process_action_data(self, action_data):
        """处理操作数据，发送消息"""
        action = action_data['action']

        if action == 'move':
            # 发送 PLAYER_FLEET_MOVE_REQUEST 消息
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVE_REQUEST, {
                "player_id": action_data["player_id"],
                "path": action_data["path"],
                "travel_method": action_data["travel_method"],
            }, self)

        # 处理降落请求
        elif action == 'land':
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_LAND_REQUEST, {
                "player_id": action_data["player_id"],
                "world_id": action_data["world_id"]
            }, self)
        # 新增起飞
        elif action == 'takeoff':
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_TAKEOFF_REQUEST, {
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

        elif action == 'explore':
            self.game.message_bus.post_message(MessageType.PLAYER_EXPLORE_WORLD_REQUEST, {
                "player_id": action_data["player_id"],
                "world_id": action_data["world_id"],
            }, self)

    def apply_modifier(self, player_id: str, modifier: Modifier, attribute: str, quantity: float, duration: int):
        pass
    
    def handle_player_resource_changed(self, message: Message):
        """
        处理玩家资源变化的消息 (由 ModifierManager 发送)
        """
        player = self.get_player_by_id(message.data["player_id"])
        if not player:
            return

        resource_id = message.data["resource_id"]
        modifier = message.data["modifier"]
        quantity = message.data["quantity"]
        if modifier == "INCREASE":
            player.modify_resource(resource_id, quantity)
        elif modifier == "REDUCE":
            player.modify_resource(resource_id, -quantity)

    def pick(self):
        if self.players:
            return random.choice(list(self.players.keys()))
        return None