from loader.enums import Modifier
from collections import defaultdict
from base_object import BaseObject

class ModifierManager(BaseObject):
    def __init__(self):
        super().__init__()
        # 存储每个目标对象的 modifier 列表，每个 modifier 是一个元组 (modifier, resource_type, quantity, duration)
        self.modifiers = defaultdict(list)

    def add_modifier(self, target, modifier, resource_type, quantity, duration):
        if isinstance(target, BaseObject):
            key = target.object_id
            self.modifiers[key].append((modifier, resource_type, quantity, duration))
        else:
            raise ValueError("target 必须是 BaseObject 的实例")

    def tick(self): 
        for target_id, modifier_list in self.modifiers.items():
            new_modifier_list = []
            for modifier, resource_type, quantity, duration in modifier_list:
                if duration > 0:
                    if modifier == Modifier.PRODUCTION:
                        target = BaseObject.get_object_by_id(target_id)
                        target[resource_type] += quantity
                    elif modifier == Modifier.COST:
                        target = BaseObject.get_object_by_id(target_id)
                        target[resource_type] -= quantity
                    elif modifier == Modifier.INCREASE:
                        target = BaseObject.get_object_by_id(target_id)
                        target[resource_type] += quantity
                        duration = 0  # 一次性增加，持续时间置为 0
                    elif modifier == Modifier.REDUCE:
                        target = BaseObject.get_object_by_id(target_id)
                        target[resource_type] -= quantity
                        duration = 0  # 一次性扣除，持续时间置为 0

                    if duration > 0:
                        new_modifier_list.append((modifier, resource_type, quantity, duration - 1))
            self.modifiers[target_id] = new_modifier_list