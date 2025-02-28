# managers/building_manager.py
from typing import Dict, List, Optional
from loader.building_config import BuildingConfig
from message_bus import MessageBus, MessageType
from base_object import BaseObject
from loader.enums import Modifier
from game import Game
import random

class BuildingInstance(BaseObject):
    def __init__(self, building_config: BuildingConfig):
        super().__init__()
        self.building_config: BuildingConfig = building_config
        self.remaining_rounds: int = building_config.build_period
        self.durability: int = building_config.durability
        self.is_under_attack: bool = False

    def check_completion(self) -> bool:
        """检查是否建造/升级完成"""
        if self.remaining_rounds > 0:
            self.remaining_rounds -= 1
            return False
        return True

    def take_damage(self, damage: int):
        """受到伤害"""
        self.durability -= damage
        if self.durability <= 0:
            self.durability = 0
            # 发送建筑被摧毁的消息
            MessageBus.post_message(MessageType.BUILDING_DESTROYED, {
                "building_id": self.object_id,
            }, self)

    def apply_modifier(self, modifier: Modifier, attribute: str, quantity: float, duration: int):
        """应用修饰符 (由 ModifierManager 调用)"""
        if modifier == Modifier.PRODUCTION:
            if attribute == "durability":  # 假设可以修改耐久度
                self.durability += int(quantity * duration)
        # 可以添加其他属性的修改


class UpgradeInstance(BaseObject):
    def __init__(self, old_building: BuildingConfig, new_building: BuildingConfig):
        super().__init__()
        self.old_building: BuildingConfig = old_building
        self.new_building: BuildingConfig = new_building
        self.remaining_rounds: int = new_building.build_period

    def check_completion(self) -> bool:
        """检查是否升级完成"""
        if self.remaining_rounds > 0:
            self.remaining_rounds -= 1
            return False
        return True


class BuildingManager():
    _instance = None

    def __new__(cls, building_configs: Dict[str, BuildingConfig], game: Game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.building_configs: Dict[str, BuildingConfig] = building_configs
            cls._instance.building_instances: Dict[str, BuildingInstance] = {}
            cls._instance.upgrade_instances: Dict[str, UpgradeInstance] = {}
            cls._instance.building_locations: Dict[str, List[str]] = {}  # world_id -> [building_id]
            cls._instance.game = game
            cls._instance.game.building_manager = cls._instance

        return cls._instance

    def get_building_config(self, building_id: str) -> Optional[BuildingConfig]:
        """根据 ID 获取建筑配置"""
        return self.building_configs.get(building_id)

    def get_building_instance(self, building_id: str) -> Optional[BuildingInstance]:
        """根据 ID 获取建筑实例"""
        return self.building_instances.get(building_id)

    def get_buildings_on_world(self, world_id: str) -> List[BuildingInstance]:
        """获取星球上的所有建筑实例"""
        return [self.building_instances[bid] for bid in self.building_locations.get(world_id, [])]

    def _add_building_instance(self, building_instance: BuildingInstance, world_id: str):
        """添加建筑实例（内部方法）"""
        self.building_instances[building_instance.object_id] = building_instance
        if world_id not in self.building_locations:
            self.building_locations[world_id] = []
        self.building_locations[world_id].append(building_instance.object_id)

    def _remove_building_instance(self, building_id: str):
        """移除建筑实例（内部方法）"""
        if building_id in self.building_instances:
            del self.building_instances[building_id]
        for world_id, building_ids in self.building_locations.items():
            if building_id in building_ids:
                building_ids.remove(building_id)

    def tick(self):
        """BuildingManager 的 tick 方法"""

        # 处理建造/升级完成
        for building_id, building_instance in list(self.building_instances.items()):
            if building_instance.check_completion():
                # 发送建造完成消息
                MessageBus.post_message(MessageType.BUILDING_COMPLETED, {
                    "building_id": building_id,
                }, self)

        for upgrade_id, upgrade_instance in list(self.upgrade_instances.items()):
            if upgrade_instance.check_completion():
                # 用新的建筑实例替换旧的
                new_building_instance = BuildingInstance(upgrade_instance.new_building)
                world_id = None
                for wid, bids in self.building_locations.items():
                    if upgrade_instance.old_building.object_id in bids:
                        world_id = wid
                        break
                if world_id:
                    self._add_building_instance(new_building_instance, world_id)

                # 发送升级完成消息
                MessageBus.post_message(MessageType.BUILDING_UPGRADE_COMPLETED, {
                    "old_building_id": upgrade_instance.old_building.object_id,
                    "new_building_id": new_building_instance.object_id,  # 新建筑的 object_id
                }, self)
                del self.upgrade_instances[upgrade_id]

        # 处理消息
        for message in MessageBus.get_messages(type=MessageType.BUILDING_REQUEST):
            self.handle_building_request(message.data)
        for message in MessageBus.get_messages(type=MessageType.BUILDING_UPGRADE_REQUEST):
            self.handle_upgrade_request(message.data)

    def handle_building_request(self, data: Dict):
        """处理建造请求"""
        player_id = data["player_id"]
        world_id = data["world_id"]
        building_id = data["building_id"]

        player = self.game.player_manager.get_player_by_id(player_id)
        world = self.game.world_manager.get_world_by_id(world_id)
        building_config = self.get_building_config(building_id)

        if not player or not world or not building_config:
            return

        # 检查资源是否足够 (现在只检查，不扣除)
        can_afford = True
        for resource_id, modifier_dict in building_config.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == "USE":
                    if player.resources.get(resource_id, 0) < quantity:
                        can_afford = False
                        break
            if not can_afford:
                break

        if not can_afford:
            # 发送资源不足消息
            MessageBus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_id": building_id,
            }, self)
            return

        for resource_id, modifier_dict in building_config.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == "USE":
                    MessageBus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                        "target_id": player_id,
                        "target_type": "Player",
                        "resource_id": resource_id,
                        "modifier": "REDUCE",  # 使用 "REDUCE" 修饰符
                        "quantity": quantity,
                        "duration": 0,  # 立即生效
                    }, self)
        # 创建建筑实例
        building_instance = BuildingInstance(building_config)
        self._add_building_instance(building_instance, world_id)

        # 发送建筑开始建造消息
        MessageBus.post_message(MessageType.BUILDING_START, {
            "building_id": building_instance.object_id,
            "world_id": world_id,
            "player_id": player_id
        }, self)

    def handle_upgrade_request(self, data: Dict):
        """处理升级请求"""
        player_id = data["player_id"]
        building_id = data["building_id"]

        player = self.game.player_manager.get_player_by_id(player_id)
        building_instance = self.get_building_instance(building_id)

        if not player or not building_instance:
            return

        # 获取下一级建筑配置
        next_level_building_config = self.get_building_config(building_instance.building_config.next_level_id)
        if not next_level_building_config:
            return

        # 检查资源是否足够 (现在只检查，不扣除)
        can_afford = True
        for resource_id, modifier_dict in next_level_building_config.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == 'USE':
                    if player.resources.get(resource_id, 0) < quantity:
                        can_afford = False
                        break
            if not can_afford:
                break

        if not can_afford:
            # 发送资源不足消息
            MessageBus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_id": building_id,
            }, self)
            return

        for resource_id, modifier_dict in next_level_building_config.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == "USE":
                    MessageBus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                        "target_id": player_id,
                        "target_type": "Player",
                        "resource_id": resource_id,
                        "modifier": "REDUCE",  # 使用 "REDUCE" 修饰符
                        "quantity": quantity,
                        "duration": 0,  # 立即生效
                    }, self)
        # 创建升级实例
        upgrade_instance = UpgradeInstance(building_instance.building_config, next_level_building_config)
        self.upgrade_instances[upgrade_instance.object_id] = upgrade_instance

        # 移除旧的建筑实例
        self._remove_building_instance(building_id)

        # 发送建筑开始升级消息
        MessageBus.post_message(MessageType.BUILDING_UPGRADE_START, {
            "old_building_id": building_id,
            "new_building_id": upgrade_instance.object_id,  # UpgradeInstance 的 object_id
            "player_id": player_id
        }, self)

    def apply_modifier(self, building_id: str, modifier: Modifier, attribute: str, quantity: float, duration: int):
        """应用修饰符到建筑 (由 ModifierManager 调用)"""
        building_instance = self.get_building_instance(building_id)
        if not building_instance:
            return

        building_instance.apply_modifier(modifier, attribute, quantity, duration)

    def pick(self):
        if self._instance.building_instances:
            return random.choice(list(self._instance.building_instances.keys()))
        return None

    def get_building_by_id(self, building_id):
        return self.building_instances.get(building_id)