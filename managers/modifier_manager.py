from typing import Dict, List, Tuple, Any, Callable
from collections import defaultdict
from loader.enums import Modifier
from .message_bus import Message, MessageType
import random

class ModifierManager():
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.modifiers: Dict[str, List[Tuple[Modifier, str, str, float, int, str]]] = defaultdict(list)
            cls._instance.game = game
            cls._instance.game.modifier_manager = cls._instance
            cls._instance.next_modifier_id: int = 1

            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.MODIFIER_PLAYER_RESOURCE, cls._instance.apply_player_resource_modifier)
            cls._instance.game.message_bus.subscribe(MessageType.MODIFIER_BUILDING, cls._instance.handle_building_modifier)
        return cls._instance

    def add_modifier(self, target_id: str, target_type: str, modifier: Modifier, attribute: str, quantity: float, duration: int):
        """添加修饰符"""
        modifier_id = str(self.next_modifier_id)
        self.next_modifier_id += 1
        self.modifiers[target_id].append((modifier, target_type, attribute, quantity, duration, modifier_id))

    def remove_modifier(self, target_id: str, modifier_id: str):
        """移除修饰符"""
        if target_id in self.modifiers:
            self.modifiers[target_id] = [
                m for m in self.modifiers[target_id] if m[5] != modifier_id
            ]

    def tick(self, tick_counter):
        """更新修饰符状态"""
        for target_id, modifier_list in list(self.modifiers.items()):
            new_modifier_list: List[Tuple[Modifier, str, str, float, int, str]] = []
            for modifier, target_type, attribute, quantity, duration, modifier_id in modifier_list:
                if duration > 0:
                    # 根据 target_type 调用相应的方法
                    if target_type == "Player":
                        # TODO 补充player的modifier逻辑
                        pass
                    elif target_type == "Building":
                        building_instance = self.game.building_manager.get_building_by_id(target_id)
                        if not building_instance:
                            continue

                        if modifier == "BUILDING" and attribute == "remaining_ticks":
                            # 递减 remaining_ticks
                            building_instance.remaining_ticks += int(quantity)

                            if building_instance.remaining_ticks <= 0:
                                # 建造/升级完成
                                self.game.message_bus.post_message(MessageType.BUILDING_COMPLETED, {"building_id": building_instance.object_id}, self)

                                # 如果是升级，更新建筑实例状态
                                if building_instance.building_config.level < 3:  # 假设最高等级是 3
                                    self.game.building_manager.upgrade_building(building_instance)

                                # 移除该 modifier
                                continue  # 直接跳过，不再添加到 new_modifier_list

                    elif target_type == "World":
                        # TODO 补充world的modifier逻辑
                        pass

                    duration -= 1
                    if duration > 0:
                        new_modifier_list.append((modifier, target_type, attribute, quantity, duration, modifier_id))
            self.modifiers[target_id] = new_modifier_list

    def apply_player_resource_modifier(self, message: Message):
        """处理修改玩家资源的请求"""
        player = self.game.player_manager.get_player_by_id(message.data["target_id"])
        if not player:
            return

        if message.data["modifier"] == Modifier.INCREASE:
            pass
        elif message.data["modifier"] == Modifier.REDUCE:
            pass

        self.game.message_bus.post_message(MessageType.PLAYER_RESOURCE_CHANGED, {
            "player_id": message.data["target_id"],
            "resource_id": message.data["resource_id"],
            "modifier":  message.data["modifier"],
            "quantity": message.data["quantity"]
        }, self)
        
    
    def handle_building_modifier(self, message: Message): #修改
        """处理建筑修改请求, 添加modifier"""
        data = message.data
        target_id: str = data["target_id"]
        target_type: str = data["target_type"]
        modifier: str = data["modifier"]
        attribute: str = data["attribute"]
        quantity: float = data["quantity"]
        duration: int = data["duration"]
        building_instance = data["building_instance"]

        # 检查是否已经存在相同类型的修饰符
        existing_modifiers = self.modifiers.get(target_id, [])
        for existing_modifier, _, existing_attribute, _, _, _ in existing_modifiers:
            if existing_modifier == modifier and existing_attribute == attribute:
                # 如果已存在相同类型的修饰符，则不添加新的修饰符
                # 或者根据需求，可以更新现有修饰符的持续时间或数量
                return

        # 添加新的修饰符
        self.add_modifier(target_id, target_type, modifier, attribute, quantity, duration)