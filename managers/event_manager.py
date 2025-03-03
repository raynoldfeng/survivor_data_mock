from typing import Dict, List, Optional, Callable
from loader.enums import Target, Modifier
from base_object import BaseObject
from .message_bus import Message, MessageType
from .player_manager import Player
from loader.event_config import EventConfig, EventPhase, EventOption, EventChallenge, EventResult
import random

class Event(BaseObject):
    def __init__(self, config: EventConfig):
        super().__init__()
        self.config: EventConfig = config
        self.current_phase: Optional[EventPhase] = None
        self.current_tick: int = 0
        self.start_tick: int = 0
        self.phase_start_tick: int = 0
        self.choices: Dict[str, str] = {}  # phase_id -> option_id
        self.target_type: Optional[Target] = None
        self.target_id: Optional[str] = None
        self.ended: bool = False

class EventManager():
    _instance = None

    def __new__(cls, event_configs: List[EventConfig], game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.event_configs: List[EventConfig] = event_configs
            cls._instance.active_events: Dict[Target, Dict[str, Event]] = {
                Target.PLAYER: {},
                Target.WORLD: {},
                Target.BUILDING: {},
            }
            cls._instance.game = game
            cls._instance.game.event_manager = cls._instance
            cls._instance.tick_interval = 30  # 每30分钟tick一次 (根据需要调整)

            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_SELECT_EVENT_OPTION, cls._instance.process_player_choice_callback)
        return cls._instance

    def generate_events(self):
        """根据概率生成新的事件"""
        for event_config in self.event_configs:
            if random.random() < event_config.trigger_probability:
                event = Event(event_config)
                event.current_phase = event_config.phases.get(event_config.initial_phase)
                event.target_type = event_config.target

                # 根据目标类型选择目标
                if event.target_type == Target.PLAYER:
                    event.target_id = self.game.player_manager.pick()
                elif event.target_type == Target.WORLD:
                    event.target_id = self.game.world_manager.pick()
                elif event.target_type == Target.BUILDING:
                    event.target_id = self.game.building_manager.pick()

                if event.target_id:
                    self.active_events[event.target_type][event.target_id] = event

                    # 发送事件开始消息
                    self.game.message_bus.post_message(MessageType.EVENT_BEGIN, {
                        "target_type": event.target_type,
                        "target_id": event.target_id,
                        "event_id": event.config.event_id,
                        "text_id": event.config.trigger_text_id,  # 事件触发文本
                    }, self)

    def process_player_choice_callback(self, message: Message): #修改
        """处理玩家的选择"""
        # event = self.active_events[Target.PLAYER].get(player_id) #移除
        player_id = message.data["player_id"]
        choice = message.data["choice"]
        event = self.active_events[Target.PLAYER].get(player_id)
        if not event:
            return

        if event.ended:
            return

        current_phase = event.current_phase
        if not current_phase:
            return

        if choice not in current_phase.options:
            return

        event.choices[current_phase.phase_id] = choice


    def evaluate_challenges(self, event: Event, option: EventOption) -> bool:
        """评估挑战是否成功"""
        target = None
        if event.target_type == Target.PLAYER:
            target = self.game.player_manager.get_player_by_id(event.target_id)
        elif event.target_type == Target.WORLD:
            target = self.game.world_manager.get_world_by_id(event.target_id)
        elif event.target_type == Target.BUILDING:
            target = self.game.building_manager.get_building_by_id(event.target_id)
        if not target:
            return False

        for challenge in option.challenges:
            value = None
            if challenge.resource_type == "morale":  # 假设有士气属性
                if isinstance(target, Player):
                    value = target.fleet.morale
            # 可以添加其他资源类型的判断

            if value is None:
                return False  # 如果没有找到对应的值，挑战失败

            if challenge.below and not value < challenge.value:
                return False
            if challenge.equal and not value == challenge.value:
                return False
            if challenge.greater and not value > challenge.value:
                return False

        return True

    def apply_event_result(self, event: Event, result_id: str):
        """应用事件结果"""
        results = event.config.results.get(result_id)
        if not results:
            return

        target = None
        if event.target_type == Target.PLAYER:
            target = self.game.player_manager.get_player_by_id(event.target_id)
        elif event.target_type == Target.WORLD:
            target = self.game.world_manager.get_world_by_id(event.target_id)
        elif event.target_type == Target.BUILDING:
            target = self.game.building_manager.get_building_by_id(event.target_id)

        if not target:
            return

        for result in results:
            if event.target_type == Target.PLAYER:
                self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                    "target_id": target.player_id,  # 使用玩家 ID 作为 target_id
                    "target_type": "Player",
                    "resource_id": result.resource_type_id,
                    "modifier": result.modifier,
                    "quantity": result.quantity,
                    "duration": result.duration,
                }, self)
            # 其他目标类型的处理 (例如，如果是 World 或 Building，可能需要发送其他类型的消息)
            elif event.target_type == Target.WORLD:
                # 假设您有一个 MODIFIER_WORLD 消息
                self.game.message_bus.post_message(MessageType.MODIFIER_WORLD, {
                    "target_id": target.object_id,
                    "target_type": "World",
                    "attribute": result.resource_type_id,  # 假设资源类型 ID 可以作为属性名
                    "modifier": result.modifier,
                    "quantity": result.quantity,
                    "duration": result.duration,
                }, self)
            elif event.target_type == Target.BUILDING:
                # 假设您有一个 MODIFIER_BUILDING 消息
                self.game.message_bus.post_message(MessageType.MODIFIER_BUILDING, {
                    "target_id": target.object_id,
                    "target_type": "Building",
                    "attribute": result.resource_type_id,  # 假设资源类型 ID 可以作为属性名
                    "modifier": result.modifier,
                    "quantity": result.quantity,
                    "duration": result.duration,
                    'building_config': target.building_config, # 传递building_config
                    'building_instance':target # 传递instance
                }, self)

    def update_event_state(self):
        """更新事件状态"""
        for target_type, events in list(self.active_events.items()):
            for target_id, event in list(events.items()):
                event.current_tick += 1

                if not event.current_phase:
                    continue

                # 检查阶段持续时间, 修改为tick判断
                if event.current_phase.duration != -1 and event.current_tick - event.phase_start_tick >= event.current_phase.duration * self.tick_interval:
                    # 阶段超时，根据情况进入下一个阶段或结束事件
                    # 这里简化处理，直接结束事件
                    event.ended = True
                    self.game.message_bus.post_message(MessageType.EVENT_END, {
                        "target_type": event.target_type,
                        "target_id": event.target_id,
                        "event_id": event.config.event_id,
                    }, self)
                    del self.active_events[target_type][target_id]
                    continue

                # 如果当前阶段有选项，并且玩家还没有做出选择，发送消息请求选择
                if event.current_phase.options and event.current_phase.phase_id not in event.choices:
                    if event.target_type == Target.PLAYER:
                        self.game.message_bus.post_message(MessageType.EVENT_NEED_OPTION, {
                            "player_id": event.target_id,
                            "event_id": event.config.event_id,
                            "phase_id": event.current_phase.phase_id,
                            "text_id": event.current_phase.text_id,
                            "options": {option_id: option.option_id for option_id, option in event.current_phase.options.items()},  # 选项的文本ID
                        }, self)

                # 如果玩家已经做出了选择，处理选择
                if event.current_phase.phase_id in event.choices:
                    choice = event.choices[event.current_phase.phase_id]
                    option = event.current_phase.options.get(choice)

                    if not option:
                        continue

                    # 评估挑战
                    success = self.evaluate_challenges(event, option)

                    # 根据挑战结果进入下一个阶段或应用结果
                    if success:
                        if option.success_result_id:
                            self.apply_event_result(event, option.success_result_id)
                        if event.current_phase.next_phase_success:
                            event.current_phase = event.config.phases.get(event.current_phase.next_phase_success)
                            event.phase_start_tick = event.current_tick
                            # 发送事件阶段变更消息
                            self.game.message_bus.post_message(MessageType.EVENT_PHASE_CHANGE, {
                                "target_type": event.target_type,
                                "target_id": event.target_id,
                                "event_id": event.config.event_id,
                                "phase_id": event.current_phase.phase_id,
                                "text_id": event.current_phase.text_id,
                            }, self)

                        else:
                            # 没有下一个阶段，事件结束
                            event.ended = True
                            self.game.message_bus.post_message(MessageType.EVENT_END, {
                                "target_type": event.target_type,
                                "target_id": event.target_id,
                                "event_id": event.config.event_id,
                            }, self)
                            del self.active_events[target_type][target_id]
                    else:
                        if option.fail_result_id:
                            self.apply_event_result(event, option.fail_result_id)
                        if event.current_phase.next_phase_failure:
                            event.current_phase = event.config.phases.get(event.current_phase.next_phase_failure)
                            event.phase_start_tick = event.current_tick
                            # 发送事件阶段变更消息
                            self.game.message_bus.post_message(MessageType.EVENT_PHASE_CHANGE, {
                                "target_type": event.target_type,
                                "target_id": event.target_id,
                                "event_id": event.config.event_id,
                                "phase_id": event.current_phase.phase_id,
                                "text_id": event.current_phase.text_id,
                            }, self)
                        else:
                            # 没有下一个阶段，事件结束
                            event.ended = True
                            self.game.message_bus.post_message(MessageType.EVENT_END, {
                                "target_type": event.target_type,
                                "target_id": event.target_id,
                                "event_id": event.config.event_id,
                            }, self)
                            del self.active_events[target_type][target_id]

    def tick(self, tick_counter):
        """
        修改后的tick方法，增加tick_counter参数, 并通过tick_interval控制频率
        """
        if tick_counter % self.tick_interval == 0:
            self.generate_events()
            self.update_event_state()