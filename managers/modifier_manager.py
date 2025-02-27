# modifier_manager.py
from typing import Dict, List, Tuple, Any
from collections import defaultdict
from loader.enums import Modifier
from base_object import BaseObject
from message_bus import MessageBus, MessageType
from game import Game
import random

class ModifierManager():
    _instance = None

    def __new__(cls, game: Game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # {target_id: [(modifier, target_type, attribute, quantity, duration, modifier_id)]}
            cls._instance.modifiers: Dict[str, List[Tuple[Modifier, str, str, float, int, str]]] = defaultdict(list)
            cls._instance.game = game
            cls._instance.game.modifier_manager = cls._instance
            cls._instance.next_modifier_id: int = 1
        return cls._instance

    def add_modifier(self, target_id: str, target_type: str, modifier: Modifier, attribute: str, quantity: float, duration: int):
        """添加修饰符"""
        modifier_id = str(self.next_modifier_id)
        self.next_modifier_id += 1
        self.modifiers[target_id].append((modifier, target_type, attribute, quantity, duration, modifier_id))

        # 发送添加修饰符的消息
        MessageBus.post_message(MessageType.ADD_MODIFIER, {
            "target_id": target_id,
            "target_type": target_type,
            "modifier": modifier,
            "attribute": attribute,  # 修改为 attribute
            "quantity": quantity,
            "duration": duration,
            "modifier_id": modifier_id
        }, self)

    def remove_modifier(self, target_id: str, modifier_id: str):
        """移除修饰符"""
        if target_id in self.modifiers:
            self.modifiers[target_id] = [
                m for m in self.modifiers[target_id] if m[5] != modifier_id
            ]

    def tick(self):
        """更新修饰符状态"""
        for target_id, modifier_list in list(self.modifiers.items()):
            new_modifier_list: List[Tuple[Modifier, str, str, float, int, str]] = []
            for modifier, target_type, attribute, quantity, duration, modifier_id in modifier_list:
                if duration > 0:
                    # 根据 target_type 调用相应的方法
                    if target_type == "Player":
                        self.game.player_manager.apply_modifier(target_id, modifier, attribute, quantity, duration)
                    elif target_type == "Building":
                        self.game.building_manager.apply_modifier(target_id, modifier, attribute, quantity, duration)
                    elif target_type == "World":
                        self.game.world_manager.apply_modifier(target_id, modifier, attribute, quantity, duration)

                    duration -= 1
                    if duration > 0:
                        new_modifier_list.append((modifier, target_type, attribute, quantity, duration, modifier_id))
            self.modifiers[target_id] = new_modifier_list

        # 处理消息
        for message in MessageBus.get_messages(sender=self):
            if message.type == MessageType.REMOVE_MODIFIER:
                self.remove_modifier(message.data["target_id"], message.data["modifier_id"])