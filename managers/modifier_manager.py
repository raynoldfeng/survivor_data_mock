from basic_types.enums import *
from basic_types.modifier import ModifierConfig, ModifierInstance
from basic_types.player import Player
from basic_types.resource import Resource
from .message_bus import Message, MessageType

#ModifierManager里负责把ModifierConfig 创建成Instance并且管理
class ModifierManager():
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.modifier_manager = cls._instance
            cls._instance.modifiers = []
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.MODIFIER_PLAYER_RESOURCE, cls._instance.handle_player_resource_modifier)
            cls._instance.game.message_bus.subscribe(MessageType.MODIFIER_BUILDING, cls._instance.handle_building_modifier)
        return cls._instance

    
    def tick(self, tick_counter):
        """更新修饰符状态"""
        modifiers_next_round = []
        for modifier in self.modifiers:
            modifier.life += 1
            config : ModifierConfig = modifier.config
            quantity = config.quantity * -1 if config.modifier_type is ModifierType.LOSS else 1
            if config.modifier_type in(ModifierType.GAIN , ModifierType.LOSS):
                if config.target_type == Target.PLAYER:
                    self.game.message_bus.post_message(MessageType.PLAYER_RESOURCE_CHANGED, {
                        "player_id": modifier.target_id,
                        "resource": config.data_type,
                        "quantity": quantity
                    }, self)
                elif config.target_type == Target.BUILDING:
                    self.game.message_bus.post_message(MessageType.BUILDING_ATTRIBUTE_CHANGED, {
                        "building_id": modifier.target_id,
                        "attribute": config.data_type,
                        "quantity": quantity
                    }, self)

                if modifier.life < config.duration:
                    modifiers_next_round.append(modifier)
            else:
                # ModifierType.CONSUME or ModifierType.PRODUCTION
                if config.target_type == Target.PLAYER:
                    self.game.message_bus.post_message(MessageType.PLAYER_RESOURCE_CHANGED, {
                        "player_id": modifier.target_id,
                        "resource": config.data_type,
                        "quantity": quantity
                    }, self)
                elif config.target_type == Target.BUILDING:
                    self.game.message_bus.post_message(MessageType.BUILDING_ATTRIBUTE_CHANGED, {
                        "building_id": modifier.target_id,
                        "attribute": config.data_type,
                        "quantity": quantity
                    }, self)
                pass
        self.modifiers = modifiers_next_round


    def handle_player_resource_modifier(self, message: Message):
        """处理修改玩家资源的请求"""
        player : Player = self.game.player_manager.get_player_by_id(message.data["target_id"])
        modifier_config : ModifierConfig = message.data["modifier_config"]

        if not player:
            return
        
        assert(isinstance(modifier_config, ModifierConfig))
        instance = ModifierInstance(target_id = player.player_id,config = modifier_config)
        self.modifiers.append(instance)

    def handle_building_modifier(self, message: Message): 
        """处理建筑修改请求, 添加modifier"""
        building = self.game.building_manager.get_building_by_id(message.data["target_id"])
        modifier_config : ModifierConfig = message.data["modifier_config"]

        assert(isinstance(modifier_config, ModifierConfig))
        instance = ModifierInstance(target_id = building.object_id,config = modifier_config)
        self.modifiers.append(instance)

