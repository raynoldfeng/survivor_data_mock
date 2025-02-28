# managers/player_manager.py
from typing import List, Dict, Optional
from message_bus import MessageBus, MessageType
from base_object import BaseObject
from loader.enums import Modifier
from loader.resource import Resource
import random
import uuid
from .robot import Robot  # 导入 Robot 类


class Fleet:
    def __init__(self):
        self.morale = 100
        self.attack = 50
        self.defense = 50
        self.location = None  # 可以是星球 ID (str) 或坐标 (tuple)
        self.destination = None  # 移动目标，可以是星球 ID 或坐标
        self.travel_start_round = 0  # 移动开始的回合
        self.travel_speed = 1.0  # 移动速度 (每回合移动的距离)
        self.travel_method = None


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


class PlayerManager():
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.players: Dict[str, Player] = {}
            cls._instance.robots: Dict[str, Robot] = {}
            cls._instance.game.player_manager = cls._instance
        return cls._instance

    def create_player(self, resources: Dict[str, Resource], building_configs):
        player = Player(resources, building_configs)
        # 获取一个随机星球的 ID
        initial_world_id = self.game.world_manager.pick()
        # 获取该星球的坐标
        initial_world = self.game.world_manager.get_world_by_id(initial_world_id)
        if initial_world:
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

    def tick(self):
        # 处理所有 Player 的 tick
        for player_id, player in self.players.items():
            action_data = player.tick(
                self.game)  # 获取 Player 的操作数据 (普通 Player 返回 None)
            if action_data:
                self.process_action_data(action_data)

        # 处理所有 Robot 的 tick
        for robot_id, robot in self.robots.items():
            action_data = robot.tick(self.game)  # 获取 Robot 的操作数据
            if action_data:
                self.process_action_data(action_data)

        for message in MessageBus.get_messages(sender=self):
            if message.type == MessageType.FLEET_MOVE_REQUEST:
                self.fleet_move_handler(message.data["player_id"], message.data["location"], message.data["destination"], message.data["travel_method"])

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

            # 玩家选择移动方式后，发送 FLEET_MOVE_REQUEST 消息
            MessageBus.post_message(MessageType.FLEET_MOVE_REQUEST, {
                "player_id": action_data["player_id"],
                "destination": destination,  # 目标是坐标
                "location": self.players[action_data["player_id"]].fleet.location,  # 当前位置
                "travel_method": action_data["travel_method"],  # 移动方式
            }, self)

            # 新增：如果玩家在移动过程中再次选择移动，则发送中断消息
            if self.players[action_data["player_id"]].fleet.destination is not None:
                MessageBus.post_message(MessageType.FLEET_MOVEMENT_INTERRUPT, {
                    "player_id": action_data["player_id"],
                }, self)

        elif action == 'build':
            MessageBus.post_message(MessageType.BUILDING_REQUEST, {
                "player_id": action_data["player_id"],
                "world_id": action_data["planet_id"],
                "building_id": action_data["building_id"],
            }, self)

        elif action == 'upgrade':
            MessageBus.post_message(MessageType.BUILDING_UPGRADE_REQUEST, {
                "player_id": action_data["player_id"],
                "building_id": action_data["building_id"],
            }, self)

        elif action == "select_event_option":
            MessageBus.post_message(MessageType.PLAYER_SELECT_EVENT_OPTION, {
                "player_id": action_data["player_id"],
                "choice": action_data["choice"],
            }, self)

    def fleet_move_handler(self, player_id: str, location, destination, travel_method):
        """处理舰队移动请求 (由 RulesManager 发送)"""
        player = self.get_player_by_id(player_id)
        if not player:
            return

        player.fleet.location = location
        player.fleet.destination = destination
        player.fleet.travel_method = travel_method


    def apply_modifier(self, player_id: str, modifier: Modifier, attribute: str, quantity: float, duration: int):
        # PlayerManager 不再直接处理资源数量的修改，只负责应用 Modifier
        # 具体的资源增减由 Player.modify_resource() 处理
        pass

    def pick(self):
        if self.players:
            return random.choice(list(self.players.keys()))
        return None