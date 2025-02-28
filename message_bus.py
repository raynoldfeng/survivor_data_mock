# message_bus.py
from enum import Enum
from typing import List, Dict, Any, Optional

class MessageType(Enum):
    NONE = 0
    EVENT_BEGIN = 1
    EVENT_PHASE_CHANGE = 2
    EVENT_NEED_OPTION = 3
    EVENT_END = 4
    PLAYER_SELECT_EVENT_OPTION = 5
    # PLAYER_RESOURCE_CHANGE = 6  # 移除，改为 MODIFIER_PLAYER_RESOURCE
    PLAYER_RESOURCE_CHANGED = 7  # 保留，用于通知资源变更结果
    PLAYER_MOVE_FLEET = 8
    PLAYER_SUBSPACE_JUMP = 9
    PLAYER_FLEET_MOVED = 10
    BUILDING_START = 11  # 保留，但现在只用于通知建筑开始建造/升级
    BUILDING_COMPLETED = 12
    BUILDING_UPGRADE_START = 13  # 保留，但现在只用于通知建筑开始升级
    BUILDING_UPGRADE_COMPLETED = 14
    BUILDING_DESTROYED = 15
    BUILDING_INSUFFICIENT_RESOURCES = 16  # 保留
    # ADD_MODIFIER = 17  # 移除，不再需要
    # REMOVE_MODIFIER = 18  # 移除，不再需要
    # MODIFIER_APPLIED = 19  # 移除，不再需要
    BUILDING_REQUEST = 20
    BUILDING_UPGRADE_REQUEST = 21
    FLEET_MOVE_REQUEST = 22
    FLEET_MOVEMENT_INTERRUPT = 23
    FLEET_ARRIVE = 24
    MODIFIER_PLAYER_RESOURCE = 25  # 新增：修改玩家资源
    MODIFIER_BUILDING = 26 #新增：修改建筑


class Message:
    def __init__(self, type: MessageType, data: Dict[str, Any], sender: Any, delay: int = 0):
        self.type: MessageType = type
        self.data: Dict[str, Any] = data
        self.sender: Any = sender
        self.age: int = 0
        self.delay: int = delay

class MessageBus:
    _messages: List[Message] = []
    MAX_AGE: int = 10

    @classmethod
    def post_message(cls, type: MessageType, data: Dict[str, Any], sender: Any, delay: int = 0):
        cls._messages.append(Message(type, data, sender, delay))

    @classmethod
    def get_messages(cls, sender: Any = None, type: Optional[MessageType] = None) -> List[Message]:
        if sender is None and type is None:
            return cls._messages[:]
        elif sender is None:
            return [msg for msg in cls._messages if msg.type == type]
        elif type is None:
            return [msg for msg in cls._messages if msg.sender == sender]
        else:
            return [msg for msg in cls._messages if msg.sender == sender and msg.type == type]

    @classmethod
    def remove_messages(cls, type: MessageType, sender: Any, **kwargs):
        cls._messages = [
            msg for msg in cls._messages
            if not (msg.type == type and msg.sender == sender and all(msg.data.get(k) == v for k, v in kwargs.items()))
        ]

    @classmethod
    def tick(cls):
        new_messages = []
        for msg in cls._messages:
            if msg.delay > 0:
                msg.delay -= 1
                new_messages.append(msg)
            else:
                msg.age += 1
                if msg.age <= cls.MAX_AGE:
                    new_messages.append(msg)
        cls._messages = new_messages