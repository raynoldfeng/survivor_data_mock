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
    MODIFIER_APPLY_REQUEST = 25
    MODIFIER_DISABLE_REQUEST = 26
    MODIFIER_RESPONSE = 27
    INTERSECTION_EVENT = 28
    WORLD_ADDED = 29
    WORLD_REMOVED = 30
    PLAYER_PURCHASE_REQUEST = 31
    PURCHASE_SUCCESS = 32

class Message:
    _msg_id_counter = 0
    def __init__(self, type: MessageType, data: Dict[str, Any], sender: Any, delay: int = 0):
        Message._msg_id_counter += 1
        self.id = Message._msg_id_counter  
        self.type: MessageType = type
        self.data: Dict[str, Any] = data
        self.sender: Any = sender
        self.delay: int = delay
        self.retries: int = 0

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
        return msg.id

    def publish_message(self, msg: Message):
        """发布消息 (立即触发回调函数)"""
        if msg.type in self.subscribers:
            for callback in self.subscribers[msg.type]:
                callback(msg)  # 调用回调函数
        
        # 按类型处理日志输出
        log_msg = f"[MSG-{msg.type.name}]"
        if msg.type == MessageType.WORLD_ADDED:
            world = msg.data.get("world")
            log_msg += f" 星球ID:{world.object_id}, 类型:{world.world_config.world_id}, 位置:{world.location}"
        elif msg.type == MessageType.WORLD_REMOVED:
            world = msg.data.get("world")
            log_msg += f" 移除星球ID:{world.object_id}, 类型:{world.world_config.world_id}"    
        elif msg.type == MessageType.EVENT_BEGIN:
            log_msg += f" 目标类型:{msg.data['target_type'].name}, 目标ID:{msg.data['target_id']}, 事件ID:{msg.data['event_id']}, 文本ID:{msg.data['text_id']}"
        elif msg.type == MessageType.EVENT_PHASE_CHANGE:
            log_msg += f" 目标类型:{msg.data['target_type'].name}, 目标ID:{msg.data['target_id']}, 事件ID:{msg.data['event_id']}, 阶段ID:{msg.data['phase_id']}"
        elif msg.type == MessageType.EVENT_NEED_OPTION:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 事件ID:{msg.data['event_id']}, 阶段ID:{msg.data['phase_id']}, 选项数:{len(msg.data['options'])}"
        elif msg.type == MessageType.EVENT_END:
            log_msg += f" 目标类型:{msg.data['target_type'].name}, 目标ID:{msg.data['target_id']}, 事件ID:{msg.data['event_id']}"
        elif msg.type == MessageType.PLAYER_SELECT_EVENT_OPTION:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 选择选项:{msg.data['choice']}"
        elif msg.type == MessageType.PLAYER_RESOURCE_CHANGED:
            # log_msg += f" 玩家ID:{msg.data['player_id']}, 资源:{msg.data['resource']}, 变化量:{msg.data['quantity']}"
            # 减少日志量
            return
        elif msg.type == MessageType.PLAYER_FLEET_MOVE_REQUEST:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 路径长度:{len(msg.data['path'])}, 方式:{msg.data['travel_method'].name}"
        elif msg.type == MessageType.PLAYER_FLEET_LAND_REQUEST:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 星球ID:{msg.data['world_id']}"
        elif msg.type == MessageType.PLAYER_FLEET_TAKEOFF_REQUEST:
            log_msg += f" 玩家ID:{msg.data['player_id']}"
        elif msg.type == MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT:
            log_msg += f" 玩家ID:{msg.data['player_id']}"
        elif msg.type == MessageType.PLAYER_FLEET_ARRIVE:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 位置:{msg.data['location']}, 类型:{msg.data['arrival_type']}"
        elif msg.type == MessageType.PLAYER_EXPLORE_WORLD_REQUEST:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 星球ID:{msg.data['world_id']}"
        elif msg.type == MessageType.BUILDING_START:
            log_msg += f" 建筑ID:{msg.data['building_id']}, 星球ID:{msg.data['world_id']}"
        elif msg.type == MessageType.BUILDING_DESTROYED:
            log_msg += f" 建筑ID:{msg.data['building_id']}, 所在星球:{self.game.building_manager.get_building_by_id(msg.data['building_id']).build_on if msg.data['building_id'] in self.game.building_manager.building_instances else '未知'}"
        elif msg.type == MessageType.BUILDING_INSUFFICIENT_RESOURCES:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 建筑ID:{msg.data['building_config'].config_id}"
        elif msg.type == MessageType.BUILDING_REQUEST:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 星球ID:{msg.data['world_id']}, 建筑类型:{msg.data['building_config_id']}"
        elif msg.type == MessageType.BUILDING_UPGRADE_REQUEST:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 原建筑ID:{msg.data['building_id']}, 建筑类型:{msg.data['building_config_id']}"
        elif msg.type == MessageType.BUILDING_ATTRIBUTE_CHANGED:
            # log_msg += f" 建筑ID:{msg.data['building_id']}, 属性:{msg.data['attribute']}, 变化量:{msg.data['quantity']}"
            # 减少日志量
            return
        elif msg.type == MessageType.MODIFIER_APPLY_REQUEST:
            log_msg += f" 目标ID:{msg.data['target_id']}, 类型:{msg.data['modifier_config'].modifier_type.name}, 数值:{msg.data['modifier_config'].quantity}"
        elif msg.type == MessageType.MODIFIER_RESPONSE:
            log_msg += f" 请求ID:{msg.data['request_id']}, 状态:{msg.data['status']}"
        elif msg.type == MessageType.INTERSECTION_EVENT:
            log_msg += f" 位置:{msg.data['location']}, 对象:{msg.data['objects']}, 坠毁:{msg.data['crash']}"
        elif msg.type == MessageType.PLAYER_PURCHASE_REQUEST:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 购买项:{msg.data['package_name']}, 数量:{msg.data['quantity']}"
        elif msg.type == MessageType.PURCHASE_SUCCESS:
            log_msg += f" 玩家ID:{msg.data['player_id']}, 购买成功: {msg.data['package_name']} x {msg.data['quantity']}"
        else:
            log_msg += f" 数据:{json.dumps(msg.data, indent=None, ensure_ascii=False)[:100]}"  # 截断过长数据

        self.game.log.info(log_msg)

    def tick(self):
        # 处理延迟消息
        new_messages = []
        for msg in self.messages:
            if msg.delay > 0:
                msg.delay -= 1  # delay的单位与基本tick间隔一致 (分钟/秒)
                new_messages.append(msg)
            else:
                self.game.log.info(f"延迟后处理消息: id:{msg.id} ,类型={msg.type.name}")
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