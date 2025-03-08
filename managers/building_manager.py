from typing import Dict, List, Optional, Union
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
        self.completion_notified = False

    def check_completion(self) -> bool:
        """检查是否建造/升级完成"""
        if self.remaining_ticks <= 0:
            return self.completion_notified

    def take_damage(self, damage: int):
        """受到伤害"""
        self.durability -= damage
        if self.durability <= 0:
            self.durability = 0
            # 发送建筑被摧毁的消息 (在tick中处理)

    def get_destroyed(self) -> bool:
        """获取是否被摧毁"""
        return self.durability <= 0


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

            # 存储每个星球上每个槽位的建筑实例 ID
            cls._instance.world_buildings: Dict[str, Dict[str, Union[List[Optional[str]], Dict[str, List[Optional[str]]]]]] = {}

            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_REQUEST, cls._instance.handle_building_request)
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_UPGRADE_REQUEST, cls._instance.handle_upgrade_request)
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_COMPLETED, cls._instance.handle_building_completed)

        return cls._instance
    
    def pick(self):
        if self.building_instances:
            return random.choice(list(self.building_instances.keys()))
        return None
    
    def get_building_config(self, building_id: str) -> Optional[BuildingConfig]:
        """根据 ID 获取建筑配置"""
        return self.building_configs.get(building_id)

    def get_building_by_id(self, building_id: str) -> Optional[BuildingInstance]:
        """根据 ID 获取建筑实例"""
        return self.building_instances.get(building_id)
    
    def add_world_slots(self, world_id: str, building_slots: Dict):
        """添加星球的初始建筑槽位信息"""
        self.world_buildings[world_id] = {}
        for slot_type, slots in building_slots.items():
            if slot_type == "resource":
                self.world_buildings[world_id][slot_type] = {}
                for subtype, count in slots.items():
                    self.world_buildings[world_id][slot_type][subtype] = [None] * count
            else:
                self.world_buildings[world_id][slot_type] = [None] * len(slots)

    def add_world_buildings(self, world_id: str, building_config: Dict):
        pass
    
    def get_buildings_on_world(self, world_id: str) -> List[BuildingInstance]:
        """获取星球上的所有建筑实例"""
        buildings = []
        if world_id in self.world_buildings:
            for slot_type, slots in self.world_buildings[world_id].items():
                if slot_type == "resource":
                    # 对于 resource 类型，需要遍历二级字典
                    for subtype, sub_slots in slots.items():
                        for building_id in sub_slots:
                            if building_id:
                                building = self.get_building_by_id(building_id)
                                if building:
                                    buildings.append(building)
                else:
                    # 对于 general 和 defense 类型，直接遍历
                    for building_id in slots:
                        building = self.get_building_by_id(building_id)
                        if building:
                            buildings.append(building)
        return buildings

    def _add_building_instance(self, building_instance: BuildingInstance, world_id: str, slot_type: str, slot_index: int, subtype: Optional[str] = None):
        """添加建筑实例（内部方法）"""
        self.building_instances[building_instance.object_id] = building_instance

        # 更新 world_buildings
        if slot_type == "resource":
            self.world_buildings[world_id][slot_type][subtype][slot_index] = building_instance.object_id
        else:
            self.world_buildings[world_id][slot_type][slot_index] = building_instance.object_id # 直接通过 slot_type 访问


    def _remove_building_instance(self, building_instance, world_id):
        """移除建筑实例及关联"""
        if building_instance.object_id in self.building_instances:
            del self.building_instances[building_instance.object_id]

        # 从 world_buildings 中移除
        if world_id in self.world_buildings:
            for slot_type, slots in self.world_buildings[world_id].items():
                if slot_type == "resource":
                    for subtype, sub_slots in slots.items():
                        try:
                            sub_slots[sub_slots.index(building_instance.object_id)] = None # 设置为None
                            return
                        except ValueError:
                            pass  # 当前 subtype 没有该建筑，继续查找
                else:
                    try:
                        # self.world_buildings[world_id][slot_type][self.world_buildings[world_id][slot_type].index(building_instance.object_id)] = None
                        self.world_buildings[world_id][slot_type][slot_type][self.world_buildings[world_id][slot_type][slot_type].index(building_instance.object_id)] = None
                        return  # 找到并移除后，直接返回
                    except ValueError:
                        pass  # 当前 slot_type 没有该建筑，继续查找

    def _has_prerequisite_building(self, building_config, world_id) -> bool:
        """检查是否有所需的前置建筑"""
        if building_config.level == 1:
            return True  # 1 级建筑没有前置

        # 构建前置建筑的 ID
        prerequisite_id_parts = building_config.building_id.split('.')
        prerequisite_id_parts[-1] = f"level{building_config.level - 1}"
        prerequisite_id = '.'.join(prerequisite_id_parts)

        # 检查前置建筑是否存在
        for building_instance in self.get_buildings_on_world(world_id):
            if building_instance.building_config.building_id == prerequisite_id:
                return True

        return False
    
    def get_available_slot(self, world_id: str, slot_type: str, subtype: Optional[str] = None) -> Optional[int]:
        """获取指定星球、类型和子类型 (可选) 的可用槽位索引"""
        if world_id not in self.world_buildings:
            return None  # 该星球没有任何建筑槽位信息

        if slot_type not in self.world_buildings[world_id]:
            return None  # 该星球没有这种类型的槽位

        if slot_type == "resource":
            # 对于 resource 类型，需要检查 subtype
            if subtype is None:
                return None  # 如果是 resource 类型，必须提供 subtype
            if subtype not in self.world_buildings[world_id][slot_type]:
                return None  # 该星球没有这种 subtype 的 resource 槽位
            try:
                # 找到 subtype 对应的列表中的第一个空闲槽位 (None)
                return self.world_buildings[world_id][slot_type][subtype].index(None)
            except ValueError:
                return None  # 该 subtype 的 resource 槽位已满
        else:
            # 对于 general 和 defense 类型，直接在列表中查找空闲槽位
            try:
                return self.world_buildings[world_id][slot_type].index(None) # 直接使用 slot_type
            except ValueError:
                return None  # 该类型的槽位已满

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
                        # planet = self.game.world_manager.get_world_by_id(planet_id) # 不需要了
                        # if planet:
                        # 遍历world_buildings 来查找
                        if planet_id in self.world_buildings:
                            for slot_type, slots in self.world_buildings[planet_id].items():
                                if slot_type == "resource":
                                    for subtype, sub_slots in slots.items():
                                        if building_id in sub_slots:
                                            world_id = planet_id
                                            # slot_index = sub_slots.index(building_id)
                                            # planet.free_slot(slot_type, slot_index, subtype)  # 释放槽位
                                            break
                                    if world_id:
                                        break
                                else:
                                    if building_id in slots[slot_type]: # 正确的
                                        world_id = planet_id
                                        # slot_index = slots.index(building_id)
                                        # planet.free_slot(slot_type, slot_index)
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

        # 检查是否有前置建筑
        if not self._has_prerequisite_building(building_config, world_id):
            self.game.log.info(f"没有前置建筑，无法建造 {building_id}。")
            return

        # 检查资源是否足够
        can_afford = True
        for modifier_data in building_config.modifiers:
            if modifier_data['modifier_type'] == Modifier.REDUCE:
                resource_id = modifier_data['resource_id']
                quantity = modifier_data['quantity']
                if player.resources.get(resource_id, 0) < quantity:
                    can_afford = False
                    break
        if not can_afford:
            # 发送资源不足消息
            self.game.message_bus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_id": building_id,
            }, self)
            return

        # 发送修改资源的请求 (使用 MODIFIER_PLAYER_RESOURCE 消息)
        for modifier_data in building_config.modifiers:
            if modifier_data['modifier_type'] == Modifier.REDUCE:
                resource_id = modifier_data['resource_id']
                quantity = modifier_data['quantity']
                self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                    "target_id": player_id,
                    "target_type": "Player",
                    "resource_id": resource_id,
                    "modifier": Modifier.REDUCE, 
                    "quantity": quantity,
                    "duration": 0,  # 立即生效
                }, self)

        # 检查是否有空闲的对应类型槽位, 并获取槽位索引
        if building_config.type == BuildingType.RESOURCE:
            slot_type = "resource"
            subtype = building_config.subtype.value  # 获取 subtype
        elif building_config.type == BuildingType.GENERAL:
            slot_type = "general"
            subtype = None
        elif building_config.type == BuildingType.DEFENSE:
            slot_type = "defense"
            subtype = None
        else:
            return  # 未知建筑类型，无法建造

        slot_index = self.get_available_slot(world_id, slot_type, subtype)  # 传入 subtype
        if slot_index is None:
            self.game.log.info("没有空闲的槽位")
            return  # 没有可用的槽位

        # 创建建筑实例
        building_instance = BuildingInstance(building_config)
        # self._add_building_instance(building_instance, world_id) # 放到后面
        # 占用星球槽位
        # world.occupy_slot(slot_type, slot_index, building_instance.object_id, subtype)
        self._add_building_instance(building_instance, world_id, slot_type, slot_index, subtype) # 在这里更新world_buildings

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

    def handle_building_completed(self, message: Message):
        data = message.data
        building_id = data["building_id"]
        building_instance = self.get_building_by_id(building_id)
        building_instance.completion_notified = True

    def handle_upgrade_request(self, message: Message):
        """处理升级请求"""
        data = message.data
        player_id = data["player_id"]
        building_id = data["building_id"]

        player = self.game.player_manager.get_player_by_id(player_id)
        building_instance = self.get_building_by_id(building_id)

        if not player or not building_instance:
            return

        # 获取下一级建筑配置
        next_level_building_config = self.get_building_config(building_instance.building_config.get_next_level_id())
        if not next_level_building_config:
            return

        # 检查资源是否足够
        can_afford = True
        for modifier_data in next_level_building_config.modifiers:
            if modifier_data['modifier_type'] == Modifier.REDUCE:
                resource_id = modifier_data['resource_id']
                quantity = modifier_data['quantity']
                if player.resources.get(resource_id, 0) < quantity:
                    can_afford = False
                    break
        if not can_afford:
            # 发送资源不足消息
            self.game.message_bus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_id": building_id,
            }, self)
            return
        # 发送修改资源的请求 (使用 MODIFIER_PLAYER_RESOURCE 消息)
        for modifier_data in next_level_building_config.modifiers:
            if modifier_data['modifier_type'] == Modifier.REDUCE:
                resource_id = modifier_data['resource_id']
                quantity = modifier_data['quantity']
                self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                    "target_id": player_id,
                    "target_type": "Player",
                    "resource_id": resource_id,
                    "modifier": Modifier.REDUCE,
                    "quantity": quantity,
                    "duration": 0,  # 立即生效
                }, self)
        
        # 获取建筑所在的星球ID
        world_id = None
        for planet_id in self.game.robot.explored_planets:
            if planet_id in self.world_buildings:
                for slot_type, slots in self.world_buildings[planet_id].items():
                    if slot_type == "resource":
                        for subtype, sub_slots in slots.items():
                            if building_id in sub_slots:
                                world_id = planet_id
                                break
                        if world_id:
                            break
                    else:
                        if building_id in slots:
                            world_id = planet_id
                            break
                if world_id:
                    break

        # 直接修改现有 building_instance 的属性
        building_instance.building_config = next_level_building_config
        building_instance.remaining_ticks = next_level_building_config.build_period
        # 可以根据需要调整 durability
        building_instance.durability = next_level_building_config.durability


        # 发送建筑开始升级消息(其实就是start消息)
        self.game.message_bus.post_message(MessageType.BUILDING_START, {
            "building_id": building_instance.object_id,  # 保持原有id
            "world_id": world_id,
            "player_id": player_id
        }, self)

        self.game.message_bus.post_message(MessageType.MODIFIER_BUILDING, {
            "target_id": building_instance.object_id,  # 保持原有 ID
            "target_type": "Building",
            "building_config": next_level_building_config,  # 传递建筑配置
            "modifier": "BUILDING",
            "attribute": "remaining_ticks",  # 修改为 remaining_ticks
            "quantity": -1 * self.tick_interval,  # 每次tick减少的量
            "duration": building_instance.remaining_ticks // self.tick_interval,  # 持续tick次数
            "building_instance": building_instance  # 传递建筑实例
        }, self)