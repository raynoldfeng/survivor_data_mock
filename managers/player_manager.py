# player_manager.py
from typing import List, Dict, Optional
from message_bus import MessageBus, MessageType
from base_object import BaseObject
from loader.enums import Modifier
import random
import uuid
class Fleet:
    def __init__(self):
        self.morale = 100,
        self.attack = 50,
        self.defense = 50,
        self.localtion = None

class Player:
    def __init__(self, resource_configs: Dict[str, float], building_config):
        self.player_id = uuid.getnode()
        self.resource_configs = {resource_id: 0 for resource_id in resource_configs.keys()}
        self.fleet = Fleet()
        self.avaliable_building_config = building_config
        self.characters = [{"name": "角色 1", "location": None}]
        self.explored_planets = []  # 维护已探索星球对象
        self.planets_buildings = {}  # 管理各个星球上的建筑实例
        self.constructing_buildings = []  # 管理正在建造的建筑实例的索引
        self.upgrading_buildings = []  # 管理正在升级的建筑实例的索引


class PlayerManager():
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.players: Dict[str, Player] = {}
            cls._instance.game = game
            cls._instance.game.player_manager = cls._instance
        return cls._instance
    
    def create_player(self, resource_configs, building_configs):
        return Player(resource_configs, building_configs)

    def add_player(self, player: Player):
        """添加玩家"""
        self.players[player.player_id] = player

    def remove_player(self, player_id: str):
        """移除玩家"""
        if player_id in self.players:
            del self.players[player_id]

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """根据 ID 获取玩家"""
        return self.players.get(player_id)

    def process_resource_change(self, player_id: str, resource_id: str, modifier: str, quantity: float, duration: int):
        """处理资源变更消息"""
        player = self.get_player_by_id(player_id)
        if not player:
            return

        if modifier == "PRODUCTION":
            # 假设您有一个 ModifierManager 来处理持续性效果
            # 这里只处理即时效果
            pass
        elif modifier == "USE":
            player.resources[resource_id] = max(0, player.resources.get(resource_id, 0) - quantity)
        elif modifier == "INCREASE":
            player.resources[resource_id] = player.resources.get(resource_id, 0) + quantity
        elif modifier == "REDUCE":
            player.resources[resource_id] = max(0, player.resources.get(resource_id, 0) - quantity)

        # 发送资源变更确认消息
        MessageBus.post_message(MessageType.PLAYER_RESOURCE_CHANGED, {
            "player_id": player_id,
            "resource_id": resource_id,
            "new_amount": player.resources.get(resource_id, 0),
        }, self)

    def move_fleet(self, player_id: str, world_id: str):
        """处理舰队移动消息"""
        player = self.get_player_by_id(player_id)
        world = self.game.world_manager.get_world_by_id(world_id)

        if not player or not world:
            return

        player.fleet.location = world
        # ... 其他舰队移动逻辑 ...

        # 发送舰队移动确认消息
        MessageBus.post_message(MessageType.PLAYER_FLEET_MOVED, {
            "player_id": player_id,
            "world_id": world_id,
        }, self)

    def tick(self):
        """PlayerManager 的 tick 方法"""
        # 处理消息
        for message in MessageBus.get_messages(sender=self):
            if message.type == MessageType.PLAYER_RESOURCE_CHANGE:
                self.process_resource_change(
                    message.data["player_id"],
                    message.data["resource_id"],
                    message.data["modifier"],
                    message.data["quantity"],
                    message.data["duration"],
                )
            elif message.type == MessageType.PLAYER_MOVE_FLEET:
                self.move_fleet(message.data["player_id"], message.data["world_id"])

    def apply_modifier(self, player_id: str, modifier: Modifier, attribute: str, quantity: float, duration: int):
        """应用修饰符到玩家 (由 ModifierManager 调用)"""
        player = self.get_player_by_id(player_id)
        if not player:
            return

        if modifier == Modifier.PRODUCTION:
            if attribute in player.resources:
                player.resources[attribute] += quantity * duration  # 假设是直接加到资源总量
        elif modifier == Modifier.COST:
            if attribute in player.resources:
                player.resources[attribute] = max(0, player.resources[attribute] - quantity * duration)
        elif modifier == Modifier.INCREASE:
             if attribute in player.resources:
                player.resources[attribute] += quantity
        elif modifier == Modifier.REDUCE:
            if attribute in player.resources:
                player.resources[attribute] = max(0, player.resources[attribute] - quantity)
        # 可以添加其他属性的修改，例如士气、舰队属性等

    def pick(self):
        """随机选择一个玩家"""
        if self._instance.players:
            return random.choice(list(self._instance.players.keys()))
        return None