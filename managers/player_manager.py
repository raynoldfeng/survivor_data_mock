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
        self.final_destination = None  # 最终目标 (单元格坐标或星球 ID)
        self.path = None  # 路径 (单元格坐标列表)
        # self.current_destination = None # 当前寻路的目标 (单元格坐标)  # 移除
        self.travel_start_round = 0
        self.travel_speed = 1.0 # 现在速度的单位是 cell/tick
        self.travel_method = None
        self.landed_on = None
        self.location = (0,0,0) # 单元格坐标

    def set_final_destination(self, destination):
        """设置最终目标"""
        self.final_destination = destination
        self.path = None  # 清空旧路径
        # self.current_destination = None # 清空旧目标  # 移除

    def set_path(self, path: List[Tuple[int, int, int]]):
        """设置路径"""
        self.path = path
        # if path:                                    # 移除
        #     self.current_destination = path[0] # 设置为路径的第一个点
        # else:
        #     self.current_destination = None

    def move_to_next_cell(self):
        """移动到路径的下一个单元格 (或朝 final_destination 移动)"""
        if self.path:
            self.path.pop(0)  # 移除当前单元格
            # if self.path:                                # 移除
            #     self.current_destination = self.path[0]  # 设置下一个单元格为目标
            # else:
            #     self.current_destination = None # 走完了
            #     self.final_destination = None  # 到达最终目的地(如果设置了路径的话)
        # 如果没有设置path, 则current_destination 为None

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
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVEMENT_ALLOWED, cls._instance.handle_fleet_movement_allowed)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_RESOURCE_CHANGED, cls._instance.handle_player_resource_changed)
        return cls._instance

    def create_player(self, resources: Dict[str, Resource], building_configs):
        player = Player(resources, building_configs)
        # 获取一个随机星球的 ID
        initial_world_id = self.game.world_manager.pick()
        # 获取该星球
        initial_world = self.game.world_manager.get_world_by_id(initial_world_id)
        if initial_world:
            # 获取出生点
            spawn_location = self.game.world_manager.get_spawn_location(initial_world)
            if spawn_location:
                self.game.log.warn(f"初始星球{initial_world.object_id}，舰队位置 {spawn_location}")
                player.fleet.location = spawn_location
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
            del self.players[player_id]

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        return self.players.get(player_id)

    def tick(self, tick_counter):
        if tick_counter % self.tick_interval == 0:
            for player_id, player in self.players.items():
                player.action_points += player.action_points_recovery_per_minute
                player.action_points = min(player.action_points, player.max_action_points)

                action_data = player.tick(self.game)
                if action_data:
                    self.process_action_data(action_data)

            for robot_id, robot in self.robots.items():
                action_data = robot.tick(self.game)
                if action_data:
                    self.process_action_data(action_data)

            # for player_id, player in self.players.items():
            #     self.move_fleet(player_id)  # 移动到rule_mgr里

    def process_action_data(self, action_data):
        """处理操作数据，发送消息"""
        action = action_data['action']

        if action == 'move':
            # 获取目标坐标
            destination = action_data["target_planet_id"]  # 先假设它是坐标或星球 ID
            target_world = self.game.world_manager.get_world_by_id(destination)
            if target_world:
                # 如果是星球 ID，则转换为星球的 cell 坐标
                destination = target_world.location

            # 发送 PLAYER_FLEET_MOVE_REQUEST 消息
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVE_REQUEST, {
                "player_id": action_data["player_id"],
                "destination": destination,  # 现在 destination 始终是 cell 坐标
                "location": self.players[action_data["player_id"]].fleet.location,
                "travel_method": action_data["travel_method"],
            }, self)

            # 如果玩家在移动过程中再次选择移动，则发送中断消息
            # if self.players[action_data["player_id"]].fleet.current_destination is not None: # 移除
            # if self.players[action_data["player_id"]].fleet.path:  # 改为判断 path 是否为空 #移除
            #     self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, {
            #         "player_id": action_data["player_id"],
            #     }, self)
        # 处理降落请求
        elif action == 'land':
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_LAND, {
                "player_id": action_data["player_id"],
                "world_id": action_data["world_id"]
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

    def handle_fleet_movement_allowed(self, message:Message):
        """
        处理舰队移动允许的消息, 现在这个消息只负责更新fleet状态
        """
        player = self.get_player_by_id(message.data["player_id"])
        if not player:
            return
        
        travel_method = message.data["travel_method"]
        destination = message.data["destination"]

        # 更新fleet状态
        player.fleet.set_final_destination(destination) #设置最终目标
        player.fleet.travel_method = travel_method
        if travel_method == "subspace_jump":
            # player.fleet.location = destination #在rules里已经设置过了
            player.fleet.landed_on = None
        elif travel_method == "slow_travel": # 新增: 如果是慢速旅行, 则设置路径
            start_location = player.fleet.location
            # 尝试寻路
            path = self.game.pathfinder.find_path(start_location, destination, target_type="world")
            if path:
                # 找到路径，设置路径
                player.fleet.set_path(path)
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
    