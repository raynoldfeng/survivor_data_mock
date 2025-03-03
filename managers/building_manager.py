from typing import Dict, List, Optional
from loader.building_config import BuildingConfig
from .message_bus import Message, MessageType
from base_object import BaseObject
from loader.enums import Modifier, BuildingType
import random

class BuildingInstance(BaseObject):
    def __init__(self, building_config: BuildingConfig):
        super().__init__()
        self.building_config: BuildingConfig = building_config
        self.remaining_ticks: int = building_config.build_period  # 使用 remaining_ticks
        self.durability: int = building_config.durability
        self.is_under_attack: bool = False

    def check_completion(self) -> bool:
        """检查是否建造/升级完成"""
        return self.remaining_ticks <= 0

    def take_damage(self, damage: int):
        """受到伤害"""
        self.durability -= damage
        if self.durability <= 0:
            self.durability = 0
            # 发送建筑被摧毁的消息 (在tick中处理)

    def get_destroyed(self) -> bool:
        """获取是否被摧毁"""
        return self.durability <= 0

    def apply_modifier(self, modifier: Modifier, attribute: str, quantity: float, duration: int):
        """应用修饰符 (由 ModifierManager 调用)"""
        if modifier == Modifier.PRODUCTION:
            if attribute == "durability":
                self.durability += int(quantity * duration)
        # 可以添加其他属性的修改

class BuildingManager():
    _instance = None

    def __new__(cls, building_configs: Dict[str, BuildingConfig], game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.building_configs: Dict[str, BuildingConfig] = building_configs
            cls._instance.building_instances: Dict[str, BuildingInstance] = {}
            cls._instance.game = game
            cls._instance.game.building_manager = cls._instance
            cls._instance.tick_interval = 5  # 每5分钟tick一次 (根据需要调整)
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_REQUEST, cls._instance.handle_building_request)
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_UPGRADE_REQUEST, cls._instance.handle_upgrade_request)

        return cls._instance

    def get_building_config(self, building_id: str) -> Optional[BuildingConfig]:
        """根据 ID 获取建筑配置"""
        return self.building_configs.get(building_id)

    def get_building_instance(self, building_id: str) -> Optional[BuildingInstance]:
        """根据 ID 获取建筑实例"""
        return self.building_instances.get(building_id)

    def get_buildings_on_world(self, world_id: str) -> List[BuildingInstance]:
        """获取星球上的所有建筑实例"""
        world = self.game.world_manager.get_world_by_id(world_id)
        if not world:
            return []
        buildings = []
        for slot_type, slots in world.building_slots.items():
            for building_id in slots:
                if building_id:
                    building = self.get_building_instance(building_id)
                    if building:
                        buildings.append(building)
        return buildings

    def _add_building_instance(self, building_instance: BuildingInstance, world_id: str):
        """添加建筑实例（内部方法）"""
        self.building_instances[building_instance.object_id] = building_instance
        # 添加到星球的建筑列表
        if world_id not in self.game.player_manager.get_player_by_id(self.game.robot.player_id).planets_buildings:
            self.game.player_manager.get_player_by_id(self.game.robot.player_id).planets_buildings[world_id] = []
        self.game.player_manager.get_player_by_id(self.game.robot.player_id).planets_buildings[world_id].append(building_instance.object_id)

    def _remove_building_instance(self, building_instance, world_id):
        """移除建筑实例及关联"""
        if building_instance.object_id in self.building_instances:
            del self.building_instances[building_instance.object_id]
        # 从星球的建筑列表中移除
        if world_id in self.game.player_manager.get_player_by_id(self.game.robot.player_id).planets_buildings:
            if building_instance.object_id in self.game.player_manager.get_player_by_id(self.game.robot.player_id).planets_buildings[world_id]:
                self.game.player_manager.get_player_by_id(self.game.robot.player_id).planets_buildings[world_id].remove(building_instance.object_id)

    def tick(self, tick_counter):
        """
        修改后的tick方法，增加tick_counter参数, 并通过tick_interval控制频率
        """
        if tick_counter % self.tick_interval == 0:
            # 处理建造/升级
            for building_id, building_instance in list(self.building_instances.items()):
                building_instance.remaining_ticks -= self.tick_interval  # 减少剩余tick数
                if building_instance.check_completion():
                    # 发送建造完成消息
                    self.game.message_bus.post_message(MessageType.BUILDING_COMPLETED, {
                        "building_id": building_id,
                    }, self)

            # 移除被摧毁的建筑
            for building_id, building_instance in list(self.building_instances.items()):
                if building_instance.get_destroyed():
                    # 获取建筑所在的星球ID
                    world_id = None
                    for planet_id in self.game.robot.explored_planets:
                        planet = self.game.world_manager.get_world_by_id(planet_id)
                        if planet:
                            for slot_type, slots in planet.building_slots.items():
                                if building_id in slots:
                                    world_id = planet_id
                                    slot_index = slots.index(building_id)
                                    planet.free_slot(slot_type, slot_index)  # 释放槽位
                                    break
                            if world_id:
                                break
                    self._remove_building_instance(building_instance, world_id)
                    # 发送建筑被摧毁的消息
                    self.game.message_bus.post_message(MessageType.BUILDING_DESTROYED, {
                        "building_id": building_id,
                    }, self)

    def handle_building_request(self, message: Message):
        """处理建造请求"""
        data = message.data
        player_id = data["player_id"]
        world_id = data["world_id"]
        building_id = data["building_id"]

        player = self.game.player_manager.get_player_by_id(player_id)
        world = self.game.world_manager.get_world_by_id(world_id)
        building_config = self.get_building_config(building_id)

        if not player or not world or not building_config:
            return

        # 检查资源是否足够
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
            self.game.message_bus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_id": building_id,
            }, self)
            return

        # 发送修改资源的请求 (使用 MODIFIER_PLAYER_RESOURCE 消息)
        for resource_id, modifier_dict in building_config.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == "USE":
                    self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                        "target_id": player_id,
                        "target_type": "Player",
                        "resource_id": resource_id,
                        "modifier": "REDUCE",
                        "quantity": quantity,
                        "duration": 0,  # 立即生效
                    }, self)

        # 检查是否有空闲的对应类型槽位, 并获取槽位索引
        if building_config.type == BuildingType.RESOURCE:
            slot_type = "resource"
        elif building_config.type == BuildingType.GENERAL:
            slot_type = "general"
        elif building_config.type == BuildingType.DEFENSE:
            slot_type = "defense"
        else:
            return  # 未知建筑类型，无法建造

        slot_index = world.get_available_slot(slot_type)
        if slot_index is None:
            self.game.log.info("没有空闲的槽位")
            return  # 没有可用的槽位

        # 创建建筑实例
        building_instance = BuildingInstance(building_config)
        self._add_building_instance(building_instance, world_id)
        # 占用星球槽位
        world.occupy_slot(slot_type, slot_index, building_instance.object_id)

        # 发送建筑开始建造消息, 并请求modifier
        self.game.message_bus.post_message(MessageType.BUILDING_START, {
            "building_id": building_instance.object_id,
            "world_id": world_id,
            "player_id": player_id
        }, self)
        self.game.message_bus.post_message(MessageType.MODIFIER_BUILDING, {
            "target_id": building_instance.object_id,
            "target_type": "Building",
            "building_config": building_config,  # 传递建筑配置
            "modifier": "BUILDING",
            "attribute": "remaining_ticks",  # 修改为 remaining_ticks
            "quantity": -1 * self.tick_interval,  # 每次tick减少的量
            "duration": building_instance.remaining_ticks // self.tick_interval,  # 持续tick次数
            "building_instance": building_instance  # 传递建筑实例
        }, self)

    def handle_upgrade_request(self, message: Message):
        """处理升级请求"""
        data = message.data
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

        # 检查资源是否足够
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
            self.game.message_bus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_id": building_id,
            }, self)
            return

        # 发送修改资源的请求 (使用 MODIFIER_PLAYER_RESOURCE 消息)
        for resource_id, modifier_dict in next_level_building_config.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == "USE":
                    self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                        "target_id": player_id,
                        "target_type": "Player",
                        "resource_id": resource_id,
                        "modifier": "REDUCE",
                        "quantity": quantity,
                        "duration": 0,  # 立即生效
                    }, self)

        # 获取建筑所在的星球ID
        world_id = None
        for planet_id in self.game.robot.explored_planets:
            planet = self.game.world_manager.get_world_by_id(planet_id)
            if planet:
                for slot_type, slots in planet.building_slots.items():
                    if building_id in slots:
                        world_id = planet_id
                        slot_index = slots.index(building_id)
                        break
                if world_id:
                    break

        # 移除旧的建筑实例
        self._remove_building_instance(building_instance, world_id)
        # 释放旧建筑占用的槽位
        if world_id:
            world = self.game.world_manager.get_world_by_id(world_id)
            if world:
                for slot_type, slots in world.building_slots.items():
                    try:
                        slot_index = slots.index(building_id)
                        world.free_slot(slot_type, slot_index)
                        break  # 找到并释放后，跳出内层循环
                    except ValueError:
                        continue  # 如果当前槽位类型中没有找到该建筑 ID，则继续查找下一个槽位类型

        # 创建新的建筑实例, 替换旧的
        new_building_instance = BuildingInstance(next_level_building_config)
        self._add_building_instance(new_building_instance, world_id)

        # 占用新建筑的槽位 (注意：这里假设升级后的建筑仍然占用相同类型的槽位)
        slot_type = next_level_building_config.type
        if slot_type == BuildingType.RESOURCE:
            slot_type = "resource"
        elif slot_type == BuildingType.GENERAL:
            slot_type = "general"
        elif slot_type == BuildingType.DEFENSE:
            slot_type = "defense"
        slot_index = world.get_available_slot(slot_type)
        if slot_index is None:
            self.game.log.warn("没有空闲的槽位")
            return  # 没有可用的槽位
        world.occupy_slot(slot_type, slot_index, new_building_instance.object_id)

        # 发送建筑开始升级消息(其实就是start消息)
        self.game.message_bus.post_message(MessageType.BUILDING_START, {
            "building_id": new_building_instance.object_id,  # 新建筑instance的id
            "world_id": world_id,
            "player_id": player_id
        }, self)

        self.game.message_bus.post_message(MessageType.MODIFIER_BUILDING, {
            "target_id": new_building_instance.object_id,  # 新建筑实例的 ID
            "target_type": "Building",
            "building_config": next_level_building_config,  # 传递建筑配置
            "modifier": "BUILDING",
            "attribute": "remaining_ticks",  # 修改为 remaining_ticks
            "quantity": -1 * self.tick_interval,  # 每次tick减少的量
            "duration": new_building_instance.remaining_ticks // self.tick_interval,  # 持续tick次数
            "building_instance": new_building_instance  # 传递建筑实例
        }, self)

    def apply_modifier(self, building_id: str, modifier: Modifier, attribute: str, quantity: float, duration: int):
        """应用修饰符到建筑 (由 ModifierManager 调用)"""
        building_instance = self.get_building_instance(building_id)
        if not building_instance:
            return

        building_instance.apply_modifier(modifier, attribute, quantity, duration)

    def pick(self):
        if self.building_instances:
            return random.choice(list(self.building_instances.keys()))
        return None

    def get_building_by_id(self, building_id):
        return self.building_instances.get(building_id)