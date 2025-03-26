from basic_types.base_object import BaseObject
from basic_types.enums import *
from basic_types.modifier import ModifierConfig, ModifierInstance
from .message_bus import Message, MessageType

class ModifierManager(BaseObject):
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.modifier_manager = cls._instance
            cls._instance.last_tick = datetime.datetime.now()
            cls._instance.modifiers= []# type: ignore
            cls._instance.modifiers_by_target: Dict[str, List[ModifierInstance]] = {} # 优化查找, key: target_id, value: list of ModifierInstance
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.MODIFIER_APPLY_REQUEST, cls._instance.handle_apply_request)
            # 新增：订阅移除 Modifier 请求
            cls._instance.game.message_bus.subscribe(MessageType.MODIFIER_REMOVE_REQUEST, cls._instance.handle_remove_request)
        return cls._instance

    def tick(self):
        now = datetime.datetime.now()
        #if (now - self.last_tick).seconds <= 1:
        #    return

        self.last_tick = now
        """更新修饰符状态"""
        modifiers_next_round = []
        try:  # 添加 try-finally 块
            for modifier in self.modifiers:
                modifier.life += 1
                config : ModifierConfig = modifier.config
                quantity = config.quantity * -1 if config.modifier_type is ModifierType.LOSS else config.quantity * 1

                # 还在Delay中
                if config.delay > 0:
                    config.delay -= 1
                    modifiers_next_round.append(modifier)  # 仍然需要添加到下一轮
                    continue

                # 开始apply
                if config.modifier_type in(ModifierType.GAIN , ModifierType.LOSS):
                    if config.target_type == ObjectType.PLAYER:
                        player = self.game.player_manager.get_player_by_id(modifier.target_id)
                        if not player:
                            succ = False
                        else:
                            resource = config.data_type
                            # 后续可以展开处理一些可以允许负值的情况
                            if  player.resources[resource] + quantity >=0:
                                succ = True
                                player.resources[resource] += quantity

                                self.game.message_bus.post_message(MessageType.PLAYER_RESOURCE_CHANGED, {
                                "player_id": modifier.target_id,
                                "resource": config.data_type,
                                "quantity": quantity
                            }, self)
                            else:
                                succ = False

                    elif config.target_type == ObjectType.BUILDING:
                        building = self.game.building_manager.get_building_by_id(modifier.target_id)
                        if not building:
                            succ = False
                        else:
                            attribute = config.data_type
                            quantity = quantity
                            old_value = getattr(building, attribute, 0)
                            new_value = old_value + quantity

                            setattr(building, attribute, new_value )

                            self.game.message_bus.post_message(MessageType.BUILDING_ATTRIBUTE_CHANGED, {
                                "building_id": modifier.target_id,
                                "attribute": config.data_type,
                                "quantity": quantity
                            }, self)

                            succ = True

                    if modifier.life < config.duration:
                        modifiers_next_round.append(modifier)
                    else:
                        self.game.message_bus.post_message(MessageType.MODIFIER_RESPONSE, {
                            "request_id": modifier.request_id,
                            "status" : succ
                        }, self)
                    # 如果是GAIN和LOSS，且已经执行完毕，就不需要添加到下一轮了

                else:
                    # ModifierType.CONSUME or ModifierType.PRODUCTION
                    modifiers_next_round.append(modifier)
                    if config.target_type == ObjectType.PLAYER:
                        player = self.game.player_manager.get_player_by_id(modifier.target_id)
                        resource = config.data_type
                        if modifier.owner_type == ObjectType.BUILDING:
                            building_instance = self.game.building_manager.get_building_by_id(modifier.owner_id)
                            # 是由building发送给Player的
                            if building_instance.building_config.manpower != 0:
                                # Habitation 类型建筑不需要manpower, 反而产出population
                                quantity = quantity * building_instance.manpower / building_instance.building_config.manpower
                        
                        expected_value = player.resources[resource] + quantity
                        if  expected_value >= 0:
                            player.resources[resource] = expected_value
                            self.game.message_bus.post_message(
                                MessageType.PLAYER_RESOURCE_CHANGED, {
                                "player_id": modifier.target_id,
                                "resource": config.data_type,
                                "quantity": quantity
                            }, self)
                        else:
                            # TODO 大概率是不够CONSUME了，需要进行处理
                            self.game.log.warn(f"Modifier 作用失败. player_id{modifier.target_id}，resource {config.data_type}, quantity:{quantity}")
                            pass


                    elif config.target_type == ObjectType.BUILDING:
                        building = self.game.building_manager.get_building_by_id(modifier.target_id)
                        if not building:
                            # 目标建筑不存在，这个 modifier 应该被移除
                            continue  # 或者 self.remove_modifier(modifier)
                        attribute = config.data_type
                        quantity = quantity
                        old_value = getattr(building, attribute, 0)
                        new_value = old_value + quantity
                        setattr(building, attribute, new_value )

                        self.game.message_bus.post_message(MessageType.BUILDING_ATTRIBUTE_CHANGED, {
                            "building_id": modifier.target_id,
                            "attribute": config.data_type,
                            "quantity": quantity
                        }, self)
        finally:
            self.modifiers = modifiers_next_round


    def handle_apply_request(self, message: Message):
        modifier_config : ModifierConfig = message.data["modifier_config"]
        assert(isinstance(modifier_config, ModifierConfig))
        instance = ModifierInstance(
            target_id = message.data["target_id"],
            config = modifier_config,
            request_id = message.id,  # 记录消息 ID
            owner_type = message.sender.type, # 记录创建者类型
            owner_id = message.sender.object_id      # 记录创建者 ID
            )

        self.modifiers.append(instance)
        # 优化：添加到按目标组织的字典
        if instance.target_id not in self.modifiers_by_target:
            self.modifiers_by_target[instance.target_id] = []
        self.modifiers_by_target[instance.target_id].append(instance)


    def handle_remove_request(self, message: Message):
        """处理移除 Modifier 的请求"""
        target_id = message.data["target_id"]
        owner_type = message.data.get("owner_type")
        owner_id = message.data.get("owner_id")
        modifier_type = message.data.get("modifier_type")

        modifiers_to_remove = []

        if target_id in self.modifiers_by_target:
            for modifier in self.modifiers_by_target[target_id]:
                # 检查 owner 信息和类型是否匹配 (更精确的筛选)
                if (owner_type is None or modifier.owner_type == owner_type) and \
                (owner_id is None or modifier.owner_id == owner_id) and \
                (modifier_type is None or modifier.config.modifier_type == modifier_type):
                    modifiers_to_remove.append(modifier)

            # 从列表中移除
            for modifier in modifiers_to_remove:
                self.modifiers.remove(modifier)
                self.modifiers_by_target[target_id].remove(modifier)
            if not self.modifiers_by_target[target_id]:
                del self.modifiers_by_target[target_id] # 清理空列表

    def remove_modifier(self, modifier_instance):
        """移除指定的 ModifierInstance"""
        if modifier_instance in self.modifiers:
            self.modifiers.remove(modifier_instance)