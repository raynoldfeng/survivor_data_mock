# event_manager.py
import random
from loader.enums import Modifier
from base_object import BaseObject

class Event(BaseObject):
    def __init__(self, name_id,trigger_probability, initial_phase):
        super().__init__()
        self.name_id = name_id
        self.trigger_probability = trigger_probability
        self.initial_phase = initial_phase
        self.phases = {}
        self.options = {}
        self.results = {}

class EventManager():
    _instance = None

    def __new__(cls, event_configs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.event_configs = event_configs
            cls._instance.event_instances = {}  # 存储每个玩家的事件实例，格式为 {player: [event_instance1, event_instance2, ...]}
        return cls._instance

    def generate_events(self, player):
        """
        根据概率为指定玩家生成事件
        """
        new_event_instances = []
        for event_config in self.event_configs:
            if random.random() < event_config.trigger_probability:
                event_instance = Event(event_config.event_name_id ,event_config.trigger_probability, event_config.initial_phase)
                event_instance.current_phase_id = event_config.initial_phase
                event_instance.start_tick = 0
                event_instance.current_tick = 0
                event_instance.ended = False
                new_event_instances.append(event_instance)
        if player not in self.event_instances:
            self.event_instances[player] = []
        self.event_instances[player].extend(new_event_instances)
        return new_event_instances

    def add_event_instance(self, player, event_instance):
        if player not in self.event_instances:
            self.event_instances[player] = []
        self.event_instances[player].append(event_instance)

    def get_event_instances(self, player):
        return self.event_instances.get(player, [])

    def tick(self, player):
        """
        事件主循环，每次循环对应一个回合
        """
        need_user_choice = []
        event_instances = self.event_instances.get(player, [])
        for event_instance in event_instances[:]:  # 使用副本进行迭代，避免在迭代过程中修改列表
            if event_instance.ended:
                continue
            current_phase = event_instance.phases.get(event_instance.current_phase_id)
            if not current_phase:
                # 没有当前阶段，事件结束
                event_instance.ended = True
                event_instances.remove(event_instance)
                continue
            event_instance.current_tick += 1
            if event_instance.current_tick - event_instance.start_tick >= current_phase.duration:
                # 检查是否需要用户选择
                if event_instance.current_phase_id in event_instance.options:
                    need_user_choice.append(event_instance)
                else:
                    # 没有选项，直接进入下一阶段
                    next_phase_id = current_phase.next_phase_success  # 这里简单假设成功，实际应根据判断逻辑确定
                    if next_phase_id:
                        event_instance.current_phase_id = next_phase_id
                        event_instance.start_tick = event_instance.current_tick
                    else:
                        # 没有后续阶段，事件结束
                        event_instance.ended = True
                        event_instances.remove(event_instance)
        return need_user_choice

    def handle_user_choice(self, player, event_instance, option_id):
        """
        处理用户选择，直接扣减玩家资源
        """
        if event_instance.ended:
            return
        current_phase = event_instance.phases.get(event_instance.current_phase_id)
        if not current_phase:
            return
        option = event_instance.options.get(event_instance.current_phase_id, {}).get(option_id)
        if not option:
            return
        result_id = option.result_id
        results = event_instance.results.get(result_id, [])
        for result in results:
            resource_type_id = result.resource_type_id
            quantity = result.quantity
            modifier = result.modifier
            if modifier == Modifier.ADD:
                player.resources[resource_type_id] = player.resources.get(resource_type_id, 0) + quantity
            elif modifier == Modifier.USE or modifier == Modifier.REDUCE:
                player.resources[resource_type_id] = max(0, player.resources.get(resource_type_id, 0) - quantity)
            # 可根据需要添加更多的 modifier 处理逻辑

        # 进入下一阶段
        next_phase_id = current_phase.next_phase_success  # 这里简单假设成功，实际应根据判断逻辑确定
        if next_phase_id:
            event_instance.current_phase_id = next_phase_id
            event_instance.start_tick = event_instance.current_tick
        else:
            # 没有后续阶段，事件结束
            event_instance.ended = True
            self.event_instances[player].remove(event_instance)