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
    PLAYER_RESOURCE_CHANGE = 6
    PLAYER_RESOURCE_CHANGED = 7
    PLAYER_MOVE_FLEET = 8
    PLAYER_FLEET_MOVED = 9
    BUILDING_START = 10
    BUILDING_COMPLETED = 11
    BUILDING_UPGRADE_START = 12
    BUILDING_UPGRADE_COMPLETED = 13
    BUILDING_DESTROYED = 14
    BUILDING_INSUFFICIENT_RESOURCES = 15
    ADD_MODIFIER = 16
    REMOVE_MODIFIER = 17
    MODIFIER_APPLIED = 18
    BUILDING_REQUEST = 19
    BUILDING_UPGRADE_REQUEST = 20

class Message:
    def __init__(self, type: MessageType, data: Dict[str, Any], sender: Any):
        self.type: MessageType = type
        self.data: Dict[str, Any] = data
        self.sender: Any = sender
        self.age: int = 0

class MessageBus:
    _messages: List[Message] = []
    MAX_AGE: int = 10  # 最大消息年龄 (可根据需要调整)

    @classmethod
    def post_message(cls, type: MessageType, data: Dict[str, Any], sender: Any):
        """发布消息"""
        cls._messages.append(Message(type, data, sender))

    @classmethod
    def get_messages(cls, sender: Any = None, type: Optional[MessageType] = None) -> List[Message]:
        """获取消息

        Args:
            sender: 消息发送者 (可选)。如果为 None，则获取所有发送者的消息。
            type: 消息类型 (可选)。如果为 None，则获取所有类型的消息。

        Returns:
            符合条件的消息列表。
        """
        if sender is None and type is None:
            return cls._messages[:]  # 返回所有消息的副本
        elif sender is None:
            return [msg for msg in cls._messages if msg.type == type]
        elif type is None:
            return [msg for msg in cls._messages if msg.sender == sender]
        else:
            return [msg for msg in cls._messages if msg.sender == sender and msg.type == type]

    @classmethod
    def remove_messages(cls, type: MessageType, sender: Any, **kwargs):
        """移除特定类型的消息

        Args:
            type: 要移除的消息类型。
            sender: 消息发送者。
            **kwargs: 其他用于过滤消息的关键字参数 (例如 player_id, building_id 等)。
        """
        cls._messages = [
            msg for msg in cls._messages
            if not (msg.type == type and msg.sender == sender and all(msg.data.get(k) == v for k, v in kwargs.items()))
        ]

    @classmethod
    def tick(cls):
        """每个 tick 更新消息年龄，并删除过期的消息"""
        for msg in cls._messages:
            msg.age += 1
        cls._messages = [msg for msg in cls._messages if msg.age <= cls.MAX_AGE]