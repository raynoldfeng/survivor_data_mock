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
                        self.game.player_manager.apply_modifier(target_id, modifier, attribute, quantity, duration)
                    elif target_type == "Building":
                        # self.game.building_manager.apply_modifier(target_id, modifier, attribute, quantity, duration)
                        # 在这里处理duration = 0的情况
                        if duration == 0:
                            continue
                        building_instance =  self.game.building_manager.get_building_instance(target_id)
                        if not building_instance:
                            continue
                        if modifier == "BUILDING":
                            if attribute == "remaining_rounds":
                                # 在这里递减 remaining_rounds
                                building_instance.remaining_rounds += int(quantity)
                                if building_instance.remaining_rounds <= 0:
                                    # 建造完成
                                    # building_instance.building_finish = True
                                    self.game.message_bus.post_message(MessageType.BUILDING_COMPLETED,{"building_id": building_instance.object_id,}, self)
                                    continue  # 跳过本次循环的剩余部分
                    elif target_type == "World":
                        self.game.world_manager.apply_modifier(target_id, modifier, attribute, quantity, duration)

                    duration -= 1
                    if duration > 0:
                        new_modifier_list.append((modifier, target_type, attribute, quantity, duration, modifier_id))
            self.modifiers[target_id] = new_modifier_list

    def apply_player_resource_modifier(self, message: Message): #修改
        """处理修改玩家资源的请求"""

        # player = self.game.player_manager.get_player_by_id(target_id) #修改
        player = self.game.player_manager.get_player_by_id(message.data["target_id"])
        if not player:
            return

        if message.data["modifier"] == "INCREASE":
            player.modify_resource(message.data["resource_id"], message.data["quantity"])
        elif message.data["modifier"] == "REDUCE":
            player.modify_resource(message.data["resource_id"], -message.data["quantity"])  # 减少资源

        self.game.message_bus.post_message(MessageType.PLAYER_RESOURCE_CHANGED, {
            "player_id": message.data["target_id"],
            "resource_id": message.data["resource_id"],
            "new_amount": player.get_resource_amount(message.data["resource_id"]),
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