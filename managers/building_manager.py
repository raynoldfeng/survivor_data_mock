from basic_types.base_object import BaseObject
from basic_types.modifier import ModifierConfig
from common import *
from loader.building_config import BuildingConfig
from basic_types.enums import *
from basic_types.building import BuildingInstance
from .message_bus import Message, MessageType

class BuildingManager(BaseObject):
    _instance = None

    def __new__(cls, building_configs: Dict[str, BuildingConfig], game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.building_configs = building_configs
            cls._instance.building_instances: Dict[str, BuildingInstance] = {} # type: ignore
            cls._instance.game = game
            cls._instance.game.building_manager = cls._instance
            cls._instance.tick_interval = 5
            cls._instance.world_buildings = {}
            cls._instance.PENDING_TIMEOUT = 60  # 超时时间 (秒)

            # 管理玩家尝试进行的建筑（发送了扣资源消息等待回应）
            cls._instance.pending_modifier_msg = {}  # {msg_id: key}
            cls._instance.pending_buildings = {}  # {key: [(msg_id, timestamp), ...]}

            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_REQUEST, cls._instance.handle_building_request)
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_UPGRADE_REQUEST, cls._instance.handle_upgrade_request)
            cls._instance.game.message_bus.subscribe(MessageType.BUILDING_ATTRIBUTE_CHANGED, cls._instance.handle_building_attribute_changed)
            cls._instance.game.message_bus.subscribe(MessageType.MODIFIER_RESPONSE, cls._instance.handle_modifier_response)

        return cls._instance

    def pick(self):
        if self.building_instances:
            return random.choice(list(self.building_instances.keys()))
        return None

    def get_building_by_id(self, building_id: str) -> Optional[BuildingInstance]:
        """根据 ID 获取建筑实例"""
        return self.building_instances.get(building_id)

    def add_world_slots(self, world_id: str, building_slots: Dict):
        """添加星球的初始建筑槽位信息"""
        self.world_buildings[world_id] = {}
        for slot_type, slots in building_slots.items():
            if slot_type == BuildingType.RESOURCE:
                self.world_buildings[world_id][slot_type] = {}
                for subtype, count in slots.items():
                    self.world_buildings[world_id][slot_type][subtype] = [None] * count
            else:
                # GENERAL, DEFENSE 类型没有二级分类
                self.world_buildings[world_id][slot_type] = [None] * slots

    def add_world_buildings(self, world_id: str, building_configs: []):
        for config_id in building_configs:
            building_config = self.get_building_config_by_id(config_id)
            if building_config:
                building_instance = BuildingInstance(building_config, world_id)
                # self._add_building_instance(world_id ...  )  # TODO: 初始建筑的添加逻辑
        pass

    def get_buildings_on_world(self, world_id: str) -> List[BuildingInstance]:
        """获取星球上的所有建筑实例"""
        buildings = []
        if world_id in self.world_buildings:
            for slot_type, slots in self.world_buildings[world_id].items():
                if slot_type == BuildingType.RESOURCE:
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

    def get_next_level_configs(self, building_config):
        next_level_building_configs = []
        for _, config in self.building_configs.items():
            if config.type == building_config.type:
                if config.subtype == building_config.subtype:
                    if config.level == building_config.level + 1:
                        next_level_building_configs.append(config)
        return next_level_building_configs

    def get_pre_level_config(self, building_config):
        for _, config in self.building_configs.items():
            if config.type == building_config.type:
                if config.subtype == building_config.subtype:
                    if config.level == building_config.level - 1:
                        return config
        return None

    def get_building_config_by_id(self, config_id):
        for _, config in self.building_configs.items():
            if config.config_id == config_id:
                return config

    def _add_building_instance(self, building_instance: BuildingInstance, world_id: str, slot_type: str, slot_index: int, subtype: Optional[str] = None):
        """添加建筑实例（内部方法）"""
        self.building_instances[building_instance.object_id] = building_instance

        # 更新 world_buildings
        if slot_type == BuildingType.RESOURCE:
            self.world_buildings[world_id][slot_type][subtype][slot_index] = building_instance.object_id
        else:
            self.world_buildings[world_id][slot_type][slot_index] = building_instance.object_id


    def _remove_building_instance(self, building_instance, world_id):
        """移除建筑实例及关联"""
        if building_instance.object_id in self.building_instances:
            del self.building_instances[building_instance.object_id]

        # 从 world_buildings 中移除
        if world_id in self.world_buildings:
            for slot_type, slots in self.world_buildings[world_id].items():
                if slot_type == BuildingType.RESOURCE:
                    for subtype, sub_slots in slots.items():
                        try:
                            sub_slots[sub_slots.index(building_instance.object_id)] = None
                        except ValueError:  # 使用 ValueError 捕获
                            pass  # 如果不在列表中，忽略
                else:
                    try:
                        index = self.world_buildings[world_id][slot_type].index(building_instance.object_id)
                        if index is not None: # 这里index可能是0
                            self.world_buildings[world_id][slot_type][index] = None
                    except ValueError: # 使用 ValueError 捕获
                        pass


        # 发送移除 Modifier 的请求 (更优雅的方式)
        self.game.message_bus.post_message(MessageType.MODIFIER_REMOVE_REQUEST, {
            "target_id": building_instance.object_id,
            "owner_type": ObjectType.BUILDING,
            "owner_id": building_instance.object_id,
            "modifier_type": ModifierType.PRODUCTION  # 只移除 PRODUCTION 和 CONSUME
        }, self)

        self.game.message_bus.post_message(MessageType.MODIFIER_REMOVE_REQUEST, {
            "target_id": building_instance.object_id,
            "owner_type": ObjectType.BUILDING,
            "owner_id": building_instance.object_id,
            "modifier_type": ModifierType.CONSUME  # 只移除 PRODUCTION 和 CONSUME
        }, self)


    def _has_prerequisite_building(self, building_config, world_id) -> bool:
        """检查是否有所需的前置建筑"""
        if building_config.level == 1:
            return True  # 1 级建筑没有前置

        # 构建前置建筑的 config_id
        prerequisite_config = self.get_pre_level_config(building_config)
        if not prerequisite_config:
            return False
        prerequisite_id = prerequisite_config.config_id

        # 检查前置建筑是否存在
        for building_instance in self.get_buildings_on_world(world_id):
            if building_instance.building_config.config_id == prerequisite_id:
                return True

        return False

    def handle_building_attribute_changed(self, message:Message):
        building = self.get_building_by_id(message.data["building_id"])
        attribute = message.data["attribute"]
        quantity = message.data["quantity"]
        player_id = self.game.world_manager.get_world_by_id(building.build_on).owner
        if attribute == "remaining_secs":
            if building.remaining_secs <=0 and building.remaining_secs - quantity >0:
                # 开始PRODUCTION
                for modifier_config in building.building_config.modifier_configs:
                    if modifier_config.modifier_type in(ModifierType.PRODUCTION , ModifierType.CONSUME):
                        msg_id = self.game.message_bus.post_message(MessageType.MODIFIER_APPLY_REQUEST, {
                        "target_id": player_id,
                        "modifier_config" : modifier_config
                        },self)


    def get_available_slot(self, world_id: str, slot_type: str, subtype: Optional[str] = None) -> Optional[int]:
        """获取指定星球、类型和子类型 (可选) 的可用槽位索引"""
        if world_id not in self.world_buildings:
            return None  # 该星球没有任何建筑槽位信息

        if slot_type not in self.world_buildings[world_id]:
            return None  # 该星球没有这种类型的槽位

        if slot_type == BuildingType.RESOURCE:
            # 对于 resource 类型，需要检查 subtype
            if subtype is None:
                return None  # 如果是 resource 类型，必须提供 subtype
            if subtype not in self.world_buildings[world_id][slot_type]:
                return None  # 该星球没有这种 subtype 的 resource 槽位
            try:
                return self.world_buildings[world_id][slot_type][subtype].index(None)
            except ValueError:
                return None

        else:
            # 对于 general 和 defense 类型，直接在列表中查找空闲槽位
            try:
                return self.world_buildings[world_id][slot_type].index(None)
            except ValueError:
                return None

    def tick(self):
        # 移除被摧毁的建筑
        for building_id, building_instance in list(self.building_instances.items()):
            if building_instance.get_destroyed():
                world_id = building_instance.build_on
                self._remove_building_instance(building_instance, world_id)
                # 发送建筑被摧毁的消息
                self.game.message_bus.post_message(MessageType.BUILDING_DESTROYED, {
                    "building_id": building_id,
                }, self)

        # 处理 pending_buildings 超时 和 确认建造/升级
        keys_to_delete = []
        for key, data_list in self.pending_buildings.items():  # 遍历 key 和 列表
            new_data_list = []  # 用于存储未超时的请求
            all_succeeded = True  # 标记是否所有 MODIFIER_APPLY_REQUEST 都成功了
            for data in data_list: # 遍历列表
                msg_id, timestamp = data  # 正确解包元组

                # 检查是否超时
                time_elapsed = datetime.datetime.now() - timestamp
                if time_elapsed.total_seconds() > self.PENDING_TIMEOUT:
                    self.game.log.warn(f"建造/升级请求的子消息超时，已取消。 key: {key}, msg_id: {msg_id}")
                    # 从 pending_modifier_msg 中移除超时的 msg_id
                    if msg_id in self.pending_modifier_msg:
                        del self.pending_modifier_msg[msg_id]
                    all_succeeded = False  # 超时也视为失败
                else:
                    # 未超时，保留
                    new_data_list.append(data)

            # 更新 pending_buildings[key] 或删除 key
            if new_data_list:
                self.pending_buildings[key] = new_data_list
            else:
                # 列表为空（所有请求都超时或完成）
                if all_succeeded:
                    # 所有请求都成功了，可以开始建造/升级
                    params = deserialize_object(key)
                    if params['action'] == PlayerAction.BUILD:
                        self.place_new_building(**params)
                    elif params['action'] == PlayerAction.UPGRADE:
                        self.upgrade_building(**params)
                # 无论成功与否，只要列表为空，都添加到待删除列表
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.pending_buildings[key]


    def place_new_building(self, **kwargs):
        world_id = kwargs['world_id']
        slot_type = kwargs['slot_type']
        slot_index = kwargs['slot_index']
        subtype = kwargs['subtype']
        building_config = kwargs['building_config']
        # 创建建筑实例
        building_instance = BuildingInstance(building_config, world_id)
        self._add_building_instance(building_instance, world_id, slot_type, slot_index, subtype)

        # 发送建筑开始建造消息, 并请求modifier
        self.game.message_bus.post_message(MessageType.BUILDING_START, {
            "building_id": building_instance.object_id,
            "world_id": world_id
        }, self)

        modifier_config =  ModifierConfig(
            data_type = "remaining_secs",
            modifier_type = ModifierType.LOSS,
            quantity = 1,
            target_type = ObjectType.BUILDING,
            duration = building_instance.building_config.build_period,
            delay = 0,
        )
        self.game.message_bus.post_message(MessageType.MODIFIER_APPLY_REQUEST, {
            "target_id": building_instance.object_id,
            "modifier_config": modifier_config
        }, self)


    def upgrade_building(self, **kwargs):
        building_id = kwargs['building_id']
        next_level_building_config_id = kwargs['building_config']
        building_instance = self.get_building_by_id(building_id)
        world_id = building_instance.build_on
        next_level_building_config = self.get_building_config_by_id(next_level_building_config_id)

        # 发送移除 Modifier 的请求 (更优雅的方式)
        self.game.message_bus.post_message(MessageType.MODIFIER_REMOVE_REQUEST, {
            "target_id": building_instance.object_id,
            "owner_type": ObjectType.BUILDING,
            "owner_id": building_instance.object_id,
            "modifier_type": ModifierType.PRODUCTION  # 只移除 PRODUCTION 和 CONSUME
        }, self)

        self.game.message_bus.post_message(MessageType.MODIFIER_REMOVE_REQUEST, {
            "target_id": building_instance.object_id,
            "owner_type": ObjectType.BUILDING,
            "owner_id": building_instance.object_id,
            "modifier_type": ModifierType.CONSUME
        }, self)

        # 替换实例的config，升级了
        building_instance.building_config = next_level_building_config
        building_instance.remaining_secs = next_level_building_config.build_period
        building_instance.durability = next_level_building_config.durability

        # 发送建筑开始升级消息(其实就是start消息)
        self.game.message_bus.post_message(MessageType.BUILDING_START, {
            "building_id": building_id,
            "world_id": world_id
        }, self)

        modifier_config =  ModifierConfig(
            data_type = "remaining_secs",
            modifier_type = ModifierType.LOSS,
            quantity = 1,
            target_type = ObjectType.BUILDING,
            duration = next_level_building_config.build_period,
            delay = 0
        )

        self.game.message_bus.post_message(MessageType.MODIFIER_APPLY_REQUEST, {
            "target_id": building_id,
            "modifier_config": modifier_config
        }, self)

    def handle_building_request(self, message: Message):
        """处理建造请求"""
        data = message.data
        player_id = data["player_id"]
        world_id = data["world_id"]
        building_config_id = data["building_config_id"]

        player = self.game.player_manager.get_player_by_id(player_id)
        world = self.game.world_manager.get_world_by_id(world_id)
        building_config = self.get_building_config_by_id(building_config_id)

        if not player or not world or not building_config:
            return

        # 检查是否有前置建筑
        if not self._has_prerequisite_building(building_config, world_id):
            self.game.log.info(f"没有前置建筑，无法建造 {building_config}。")
            return

        # 检查资源是否足够
        can_afford = True
        for modifier_config in building_config.modifier_configs:
            if modifier_config.modifier_type == ModifierType.LOSS:
                resource = modifier_config.data_type
                quantity = modifier_config.quantity
                if player.resources.get(resource, 0) < quantity:
                    can_afford = False
                    break

        if not can_afford:
            # 发送资源不足消息
            self.game.message_bus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_config_id": building_config_id,
            }, self)
            return

        # 检查是否有空闲的对应类型槽位, 并获取槽位索引
        if building_config.type == BuildingType.RESOURCE:
            slot_type = building_config.type
            subtype = building_config.subtype
        elif building_config.type == BuildingType.GENERAL:
            slot_type = building_config.type
            subtype = None
        elif building_config.type == BuildingType.DEFENSE:
            slot_type = building_config.type
            subtype = None
        else:
            return  # 未知建筑类型，无法建造

        slot_index = self.get_available_slot(world_id, slot_type, subtype)
        if slot_index is None:
            self.game.log.info("没有空闲的槽位")
            return  # 没有可用的槽位


        one_shot_modifiers = 0
        building_params = {
            "action" : PlayerAction.BUILD,
            "building_config" : building_config,
            "world_id" : world_id,
            "slot_type" : slot_type,
            "slot_index" : slot_index,
            "subtype" :subtype
        }

        # 发送修改资源的请求
        for modifier_config in building_config.modifier_configs:
            if modifier_config.modifier_type in(ModifierType.GAIN , ModifierType.LOSS):
                msg_id = self.game.message_bus.post_message(MessageType.MODIFIER_APPLY_REQUEST, {
                "target_id": player_id,
                "modifier_config" : modifier_config
                },self)

                key = serialize_object(building_params)
                self.pending_modifier_msg[msg_id] = key
                if key not in self.pending_buildings:
                    self.pending_buildings[key] = []

                self.pending_buildings[key].append((msg_id, datetime.datetime.now()))
                one_shot_modifiers += 1

        if one_shot_modifiers == 0:
            self.place_new_building(**building_params)

    def handle_upgrade_request(self, message: Message):
        """处理升级请求"""
        data = message.data
        player_id = data["player_id"]
        building_id = data["building_id"]
        building_config_id = data["building_config_id"]

        player = self.game.player_manager.get_player_by_id(player_id)
        building_instance = self.get_building_by_id(building_id)
        next_level_config = self.get_building_config_by_id(building_config_id)
        if not player or not building_instance:
            return

        # 获取下一级建筑配置
        next_level_building_configs = self.get_next_level_configs(building_instance.building_config)
        if not any(building_config_id == config.config_id for config in next_level_building_configs):
            return

        # 检查资源是否足够
        can_afford = True
        for modifier_config in next_level_config.modifier_configs:
            if modifier_config.modifier_type == ModifierType.LOSS:
                resource = modifier_config.data_type
                quantity = modifier_config.quantity
                if player.resources.get(resource, 0) < quantity:
                    can_afford = False
                    break

        if not can_afford:
            # 发送资源不足消息
            self.game.message_bus.post_message(MessageType.BUILDING_INSUFFICIENT_RESOURCES, {
                "player_id": player_id,
                "building_config_id": building_config_id,
            }, self)
            return

        one_shot_modifiers = 0
        upgrade_params ={
            "action" : PlayerAction.UPGRADE,
            "building_id" : building_instance.object_id,
            "building_config" : building_config_id
        }

        # 发送修改资源的请求
        for modifier_config in next_level_config.modifier_configs:
            if modifier_config.modifier_type in(ModifierType.GAIN , ModifierType.LOSS):
                msg_id = self.game.message_bus.post_message(MessageType.MODIFIER_APPLY_REQUEST, {
                "target_id": player_id,
                "modifier_config" : modifier_config
                },self)

                key = serialize_object(upgrade_params)
                self.pending_modifier_msg[msg_id] = key
                if key not in self.pending_buildings:
                    self.pending_buildings[key] = []

                self.pending_buildings[key].append((msg_id, datetime.datetime.now()))
                one_shot_modifiers += 1

        if one_shot_modifiers == 0:
            self.upgrade_building(**upgrade_params)

    def handle_modifier_response(self, msg):
        index = msg.data["request_id"]
        succ = msg.data["status"]
        if index in self.pending_modifier_msg:
            key = self.pending_modifier_msg[index]
            del self.pending_modifier_msg[index]
            if not succ:
                # 失败了，直接去掉后续流程, 从 pending_buildings 中移除 key
                if key in self.pending_buildings:
                    del self.pending_buildings[key]
            else:
                # 成功了，从 pending_buildings[key] 中移除对应的 (msg_id, timestamp)
                if key in self.pending_buildings:
                    new_data_list = []
                    for data in self.pending_buildings[key]:
                        msg_id, timestamp = data
                        if msg_id != index:  # 保留不是 index 的
                            new_data_list.append(data)
                    # 不要在这里删除 key！
                    self.pending_buildings[key] = new_data_list