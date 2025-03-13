from basic_types.modifier import ModifierConfig
from common import *
from loader.building_config import BuildingConfig
from basic_types.enums import *
from basic_types.building import BuildingInstance
from .message_bus import Message, MessageType

class BuildingManager():
    _instance = None

    def __new__(cls, building_configs: Dict[str, BuildingConfig], game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.building_configs: Dict[str, BuildingConfig] = building_configs # type: ignore
            cls._instance.building_instances: Dict[str, BuildingInstance] = {} # type: ignore
            cls._instance.game = game
            cls._instance.game.building_manager = cls._instance
            cls._instance.tick_interval = 5 

            # 存储每个星球上每个槽位的建筑实例 ID
            cls._instance.world_buildings: Dict[str, Dict[str, Union[List[Optional[str]], Dict[str, List[Optional[str]]]]]] = {}

            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_REQUEST, cls._instance.handle_building_request)
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_UPGRADE_REQUEST, cls._instance.handle_upgrade_request)
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_COMPLETED, cls._instance.handle_building_completed)
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_ATTRIBUTE_CHANGED, cls._instance.handle_building_attribute_changed)
            

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
                    for building_id in slots: # 修正：直接使用 slots
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
                        self.world_buildings[world_id][slot_type][self.world_buildings[world_id][slot_type].index(building_instance.object_id)] = None # 修正：使用索引
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
    
    def handle_building_attribute_changed(self, message:Message):
        building = self.get_building_by_id(message.data["building_id"])
        if not building:
            return

        attribute = message.data["attribute"]
        quantity = message.data["quantity"]

        # 这里后续改成明确的对象方法调用，不要对象/dict混用
        old_value = getattr(building, attribute, 0)
        new_value = old_value + quantity
        setattr(building, attribute, new_value )

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

    def get_world_by_building(self, building_id):
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

    def tick(self, tick_counter):
        if tick_counter % self.tick_interval == 0:
            # 移除被摧毁的建筑
            for building_id, building_instance in list(self.building_instances.items()):
                if building_instance.get_destroyed():
                    world_id = self.get_world_by_building(building_id)
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

        for modifier_config in building_config.modifier_configs:
            if modifier_config.modifier_type == ModifierType.LOSS:
                resource = modifier_config.data_type
                quantity = modifier_config.quantity
                if player.resources.get(resource.id, 0) < quantity:
                    can_afford = False
                    break

        # manpower 是单独处理的
        manpower = building_config.manpower
        

        if not can_afford:
            # 发送资源不足消息
            self.game.message_bus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_id": building_id,
            }, self)
            return

        # 发送修改资源的请求 (使用 MODIFIER_PLAYER_RESOURCE 消息)
        for modifier_config in building_config.modifier_configs:
            data_type = modifier_config.data_type
            quantity = modifier_config.quantity
            self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                "target_id": player_id,
                "modifier_config" : modifier_config
                }, self)

        # 检查是否有空闲的对应类型槽位, 并获取槽位索引
        if building_config.type == BuildingType.RESOURCE:
            slot_type = "resource"
            subtype = building_config.subtype.value
        elif building_config.type == BuildingType.GENERAL:
            slot_type = "general"
            subtype = None
        elif building_config.type == BuildingType.DEFENSE:
            slot_type = "defense"
            subtype = None
        else:
            return  # 未知建筑类型，无法建造

        slot_index = self.get_available_slot(world_id, slot_type, subtype)
        if slot_index is None:
            self.game.log.info("没有空闲的槽位")
            return  # 没有可用的槽位

        # 创建建筑实例
        building_instance = BuildingInstance(building_config)
        self._add_building_instance(building_instance, world_id, slot_type, slot_index, subtype)

        # 发送建筑开始建造消息, 并请求modifier
        self.game.message_bus.post_message(MessageType.BUILDING_START, {
            "building_id": building_instance.object_id,
            "world_id": world_id,
            "player_id": player_id
        }, self)
        
        modifier_config =  ModifierConfig(
            data_type = "remaining_ticks",  # 修改为 remaining_ticks
            modifier_type = ModifierType.LOSS,
            quantity = self.tick_interval,  # 每次tick减少的量
            target_type = Target.BUILDING,
            duration = building_instance.building_config.build_period // self.tick_interval,  # 持续tick次数, 改为使用升级时间
            delay = 0,
        )
        self.game.message_bus.post_message(MessageType.MODIFIER_BUILDING, {
            "target_id": building_instance.object_id,
            "modifier_config": modifier_config
        }, self)

    def handle_building_completed(self, message: Message):
        pass 

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
        for modifier_config in next_level_building_config.modifier_configs:
            if modifier_config.modifier_type == ModifierType.LOSS:
                resource = modifier_config.data_type
                quantity = modifier_config.quantity
                if player.resources.get(resource.id, 0) < quantity:
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
        for modifier_config in next_level_building_config.modifier_configs:
            resource_id = modifier_config.data_type
            quantity = modifier_config.quantity
            self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                "target_id": player_id,
                "target_type": Target.PLAYER,
                "resource_id": resource_id,
                "modifier_config": modifier_config,
                "quantity": quantity,
            }, self)
        
        building_id = building_instance.object_id
        world_id = self.get_world_by_building(building_id)

        #替换实例的coinfig，升级了
        building_instance.building_config = next_level_building_config
        building_instance.remaining_ticks = next_level_building_config.build_period
        building_instance.durability = next_level_building_config.durability

        # 发送建筑开始升级消息(其实就是start消息)
        self.game.message_bus.post_message(MessageType.BUILDING_START, {
            "building_id": building_id,  # 保持原有id
            "world_id": world_id,
            "player_id": player_id
        }, self)

        modifier_config =  ModifierConfig(
            data_type = "remaining_ticks",
            modifier_type = ModifierType.LOSS,
            quantity = self.tick_interval,  # 每次tick减少的量
            target_type = Target.BUILDING,
            duration = next_level_building_config.build_period // self.tick_interval,  # 持续tick次数, 改为使用升级时间
            delay = 0,
        )

        self.game.message_bus.post_message(MessageType.MODIFIER_BUILDING, {
            "target_id": building_id,
            "modifier_config": modifier_config
        }, self)
    
