from basic_types.base_object import BaseObject
from basic_types.modifier import ModifierConfig
from basic_types.player import Player
from basic_types.basic_typs import Vector3
from basic_types.enums import *
from common import *
from loader.resource import Resource
from .message_bus import MessageType, Message
from .robot import Robot

class PlayerManager(BaseObject):
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.players: Dict[str, Player] = {} # type: ignore
            cls._instance.robots: Dict[str, Robot] = {} # type: ignore
            cls._instance.game.player_manager = cls._instance
            cls._instance.tick_interval = 1
            # 新增：存储每个玩家舰队的位置
            cls._instance.fleet_locations: Dict[Vector3, List[str]] = {} # type: ignore
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_RESOURCE_CHANGED, cls._instance.handle_player_resource_changed)
        return cls._instance

    def create_player(self, resources, building_configs, purchase_configs): 
        player = Player(resources, building_configs, purchase_configs)
        initial_world_id = self.game.world_manager.pick()
        initial_world = self.game.world_manager.get_world_by_id(initial_world_id)
        if initial_world:
            spawn_location = initial_world.get_spawn_location()
            if spawn_location:
                self.game.log.warn(f"初始星球{initial_world.object_id}，舰队位置 {spawn_location}")
                player.fleet.location = spawn_location
                # 新增：将玩家的初始舰队位置添加到 fleet_locations
                self.fleet_locations[player.fleet.location] = [player.object_id]
            else:
                self.game.log.warn(f"无法为星球 {initial_world.object_id} 找到可到达的出生点，将舰队位置设置为 (0, 0, 0)")
                player.fleet.location = Vector3(0, 0, 0)
        else:
            self.game.log.warn("找不到初始星球，将舰队位置设置为 (0, 0, 0)")
            player.fleet.location = Vector3(0, 0, 0)
        self.add_player(player)
        return player

    def add_robot(self, player):  # 移除 purchase_configs 参数
        """添加 Robot"""
        self.robots[player.object_id] = Robot(player.object_id, self.game)  # 不再传递 purchase_configs
        return player
    
    def add_player(self, player: Player):
        self.players[player.object_id] = player

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
    
    def update_fleet_location(self, player_id: str, old_location: Vector3, new_location: Vector3):
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

    def process_action_data(self, action_data):
        """处理操作数据，发送消息"""
        action = action_data['action']

        if action == PlayerAction.MOVE:
            # 发送 PLAYER_FLEET_MOVE_REQUEST 消息
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVE_REQUEST, {
                "player_id": action_data["player_id"],
                "path": action_data["path"],
                "travel_method": action_data["travel_method"],
            }, self)

        # 处理降落请求
        elif action == PlayerAction.LAND:
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_LAND_REQUEST, {
                "player_id": action_data["player_id"],
                "world_id": action_data["world_id"]
            }, self)
        # 新增起飞
        elif action == PlayerAction.TAKEOFF:
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_TAKEOFF_REQUEST, {
                "player_id": action_data["player_id"],
            }, self)

        elif action == PlayerAction.BUILD:
            self.game.message_bus.post_message(MessageType.BUILDING_REQUEST, {
                "player_id": action_data["player_id"],
                "world_id": action_data["planet_id"],
                "building_config_id": action_data["building_config_id"],
            }, self)

        elif action == PlayerAction.UPGRADE:
            self.game.message_bus.post_message(MessageType.BUILDING_UPGRADE_REQUEST, {
                "player_id": action_data["player_id"],
                "building_id": action_data["building_id"],
                "building_config_id": action_data["building_config_id"],
            }, self)

        elif action == PlayerAction.CHOICE:
            self.game.message_bus.post_message(MessageType.PLAYER_SELECT_EVENT_OPTION, {
                "player_id": action_data["player_id"],
                "choice": action_data["choice"],
            }, self)

        elif action == PlayerAction.EXPLORE:
            self.game.message_bus.post_message(MessageType.PLAYER_EXPLORE_WORLD_REQUEST, {
                "player_id": action_data["player_id"],
                "world_id": action_data["world_id"],
            }, self)
            
        elif action == PlayerAction.PURCHASE: #修改这里
            self.game.message_bus.post_message(MessageType.PLAYER_PURCHASE_REQUEST, { #修改这里
                "player_id": action_data["player_id"],
                "package_name": action_data["name"],
                "quantity" : action_data["quantity"]
            }, self)

        elif action == PlayerAction.ALLOCATE_MANPOWER:
            self.allocate_manpower(action_data["player_id"], action_data["building_id"], action_data["amount"])

    def handle_player_resource_changed(self, message: Message):
        """
        处理玩家资源变化的消息 (由 ModifierManager 发送)
        """
        pass


    def allocate_manpower(self,player_id, building_id: str, amount: int):
        """
        向指定建筑分配人力。
        """
        building = self.game.building_manager.get_building_by_id(building_id)
        if not building:
            return

        world_id = building.build_on
        if world_id not in self.players[player_id].manpower_allocation:
            self.players[player_id].manpower_allocation[world_id] = {}

        # 更新 Player 的 manpower_allocation
        self.players[player_id].manpower_allocation[world_id][building_id] = \
            self.players[player_id].manpower_allocation.get(world_id, {}).get(building_id, 0) + amount

        # 发送 BUILDING_ATTRIBUTE_CHANGED 消息
        self.game.message_bus.post_message(MessageType.BUILDING_ATTRIBUTE_CHANGED, {
            "building_id": building_id,
            "attribute": "manpower",
            "quantity": amount,  # 正数表示增加，负数表示减少
        }, self)

    def pick(self):
        if self.players:
            return random.choice(list(self.players.keys()))
        return None
    
    def tick(self):
        for player_id, player in self.players.items():
            player.calculate_available_manpower()
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