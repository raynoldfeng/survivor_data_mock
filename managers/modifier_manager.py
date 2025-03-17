from basic_types.base_object import BaseObject
from basic_types.enums import *
from basic_types.modifier import ModifierConfig, ModifierInstance
from basic_types.player import Player
from .message_bus import Message, MessageType

#ModifierManager里负责把ModifierConfig 创建成Instance并且管理
class ModifierManager(BaseObject):
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.modifier_manager = cls._instance
            cls._instance.modifiers= []# type: ignore
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.MODIFIER_APPLY_REQUEST, cls._instance.handle_apply_request)
        return cls._instance

    
    def tick(self, tick_counter):
        """更新修饰符状态"""
        modifiers_next_round = []
        for modifier in self.modifiers:
            modifier.life += 1
            config : ModifierConfig = modifier.config
            quantity = config.quantity * -1 if config.modifier_type is ModifierType.LOSS else 1
            
            # 还在Delay中
            if config.delay > 0:
                config.delay -= 1
                continue
            
            # 开始apply
            if config.modifier_type in(ModifierType.GAIN , ModifierType.LOSS):
                if config.target_type == ObjectType.PLAYER:
                    self.game.message_bus.post_message(MessageType.PLAYER_RESOURCE_CHANGED, {
                        "player_id": modifier.target_id,
                        "resource": config.data_type,
                        "quantity": quantity
                    }, self)
                elif config.target_type == ObjectType.BUILDING:
                    self.game.message_bus.post_message(MessageType.BUILDING_ATTRIBUTE_CHANGED, {
                        "building_id": modifier.target_id,
                        "attribute": config.data_type,
                        "quantity": quantity
                    }, self)

                if modifier.life < config.duration:
                    modifiers_next_round.append(modifier)
                else:
                    self.game.message_bus.post_message(MessageType.MODIFIER_RESPONSE, {
                        "request_id": modifier.request_id
                    }, self)
                    
            else:
                # ModifierType.CONSUME or ModifierType.PRODUCTION
                modifiers_next_round.append(modifier)
                if config.target_type == ObjectType.PLAYER:
                    self.game.message_bus.post_message(
                        MessageType.PLAYER_RESOURCE_CHANGED, {
                        "player_id": modifier.target_id,
                        "resource": config.data_type,
                        "quantity": quantity
                    }, self)

                elif config.target_type == ObjectType.BUILDING:
                    self.game.message_bus.post_message(MessageType.BUILDING_ATTRIBUTE_CHANGED, {
                        "building_id": modifier.target_id,
                        "attribute": config.data_type,
                        "quantity": quantity
                    }, self)


        self.modifiers = modifiers_next_round


    def handle_apply_request(self, message: Message):
        modifier_config : ModifierConfig = message.data["modifier_config"]
        assert(isinstance(modifier_config, ModifierConfig))
        instance = ModifierInstance(
            target_id = message.data["target_id"],
            config = modifier_config, 
            request_id = message.id,
            owner_type = message.sender.object_type,
            owner_id = message.sender.object_id
            )


        self.modifiers.append(instance)
