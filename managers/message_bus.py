from enum import Enum
from common import *

class MessageType(Enum):
    NONE = 0
    EVENT_BEGIN = 1
    EVENT_PHASE_CHANGE = 2
    EVENT_NEED_OPTION = 3
    EVENT_END = 4
    PLAYER_SELECT_EVENT_OPTION = 5
    PLAYER_RESOURCE_CHANGED = 6
    PLAYER_SUBSPACE_JUMP = 7
    PLAYER_FLEET_MOVE_REQUEST = 8
    PLAYER_FLEET_MOVE = 9
    PLAYER_FLEET_LAND_REQUEST = 10 
    PLAYER_FLEET_TAKEOFF_REQUEST = 11
    PLAYER_FLEET_MOVEMENT_INTERRUPT = 12
    PLAYER_FLEET_ARRIVE = 13
    PLAYER_FLEET_MOVEMENT_ALLOWED = 14
    PLAYER_EXPLORE_WORLD_REQUEST = 15
    BUILDING_START = 16
    BUILDING_COMPLETED = 17
    BUILDING_UPGRADE_START = 18
    BUILDING_UPGRADE_COMPLETED = 19
    BUILDING_DESTROYED = 20
    BUILDING_INSUFFICIENT_RESOURCES = 21
    BUILDING_REQUEST = 22
    BUILDING_UPGRADE_REQUEST = 23
    BUILDING_ATTRIBUTE_CHANGED = 24
    MODIFIER_PLAYER_RESOURCE = 25
    MODIFIER_BUILDING = 26
    MODIFIER_WORLD = 27
    INTERSECTION_EVENT = 28



class Message:
    _msg_id_counter = 0
    def __init__(self, type: MessageType, data: Dict[str, Any], sender: Any, delay: int = 0):
        Message._msg_id_counter += 1
        self.id = Message._msg_id_counter  
        self.type: MessageType = type
        self.data: Dict[str, Any] = data
        self.sender: Any = sender
        # self.age: int = 0 #移除
        self.delay: int = delay
        self.retries: int = 0  # 新增：重试次数
        # self.is_consumed = False  # 移除 is_consumed 属性

class MessageBus:

    def __init__(self, game):
        self.game = game
        self.messages: List[Message] = []  # 延迟消息队列
        self.pending_messages: List[Message] = []  # 未成功处理的消息队列
        self.subscribers: Dict[MessageType, List[Callable[[Message], None]]] = {}  # 订阅者字典
        self.MAX_RETRIES = 3  # 最大重试次数

    def subscribe(self, message_type: MessageType, callback: Callable[[Message], None]):
        """订阅消息"""
        if message_type not in self.subscribers:
            self.subscribers[message_type] = []
        self.subscribers[message_type].append(callback)

    def unsubscribe(self, message_type: MessageType, callback: Callable[[Message], None]):
        """取消订阅"""
        if message_type in self.subscribers:
            self.subscribers[message_type].remove(callback)

    def post_message(self, type: MessageType, data: Dict[str, Any], sender: Any, delay: int = 0):
        msg = Message(type, data, sender, delay)
        if delay > 0:
            self.messages.append(msg)  # 延迟消息添加到 messages 列表
        else:
            self.publish_message(msg)  # 立即发布消息

    def publish_message(self, msg: Message):
        """发布消息 (立即触发回调函数)"""
        self.game.log.info(f"发布消息: id:{msg.id}, 类型={msg.type.name}, 数据:{msg.data}, 发送者={msg.sender}")
        if msg.type in self.subscribers:
            for callback in self.subscribers[msg.type]:
                try:
                    callback(msg)  # 调用回调函数
                except Exception as e:
                    self.game.log.error(f"处理消息 {msg.id} ({msg.type.name}) 时发生错误: {e}")
                    # 将消息添加到 pending_messages 列表，稍后重试
                    # msg.retries = 0 # 这里不能初始化0
                    self.pending_messages.append(msg)
                    return  # 如果有回调函数出错，则停止处理

    def tick(self, tick_counter):
        # 处理延迟消息
        new_messages = []
        for msg in self.messages:
            if msg.delay > 0:
                msg.delay -= 1  # delay的单位与基本tick间隔一致 (分钟/秒)
                new_messages.append(msg)
            else:
                self.game.log.info(f"延迟后处理消息: id:{msg.id} ,类型={msg.type.name}, 数据:{msg.data}, 发送者={msg.sender}")
                # 立即发布消息
                self.publish_message(msg)
        self.messages = new_messages

        temp_pending_messages = []
        for msg in self.pending_messages:
            msg.retries += 1
            if msg.retries <= self.MAX_RETRIES:
                self.game.log.info(f"重试消息: id:{msg.id}, 类型={msg.type.name}, 重试次数={msg.retries}")
                self.publish_message(msg)  # 重新发布消息
                temp_pending_messages.append(msg) #放到临时列表里
            else:
                self.game.log.error(f"消息 {msg.id} ({msg.type.name}) 超过最大重试次数，已丢弃")
        self.pending_messages = temp_pending_messages