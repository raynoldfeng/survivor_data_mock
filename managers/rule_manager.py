from typing import Dict, List, Tuple, Any
from .message_bus import MessageType, Message

class RulesManager:
    _instance = None

    SUBSPACE_JUMP_COST = 10
    # SLOW_TRAVEL_MAX_DISTANCE = 10.0 #保留
    ACTION_POINTS_PER_DISTANCE = 1  # 每单位距离消耗的行动点数 (根据需要调整)

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.rule_manager = cls._instance
            cls._instance.tick_interval = 1  # 每分钟tick一次 (根据您的基本tick间隔设置)
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVE_REQUEST, cls._instance.handle_fleet_move_request)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, cls._instance.handle_fleet_movement_interrupt) #保留
        return cls._instance

    def tick(self, tick_counter):
        """
        修改后的tick方法，增加tick_counter参数
        """
        if tick_counter % self.tick_interval == 0:
            # self.update_fleet_positions() #移除
            self.check_fleet_proximity()  # 新增：检查舰队邻近, 并且发送抵达事件

    def handle_fleet_move_request(self, message: Message):  # 修改
        """处理舰队移动请求 (由 PlayerManager 发送)"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        destination = message.data["destination"]
        travel_method = message.data["travel_method"]

        if not player:
            return

        if travel_method == "subspace_jump":
            cost = self.SUBSPACE_JUMP_COST
            if player.get_resource_amount("promethium") >= cost:
                # 发送允许移动消息, 扣除资源
                self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                    "target_id": player.player_id,
                    "target_type": "Player",
                    "resource_id": "promethium",
                    "modifier": "REDUCE",
                    "quantity": cost,
                    "duration": 0,
                }, self)
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_ALLOWED, {
                    "player_id": player.player_id,
                    "destination": destination,
                    "travel_method": travel_method,
                    # "cost": cost, #移除
                }, self)
            else:
                self.game.log.warn(f"玩家 {player.player_id} 尝试亚空间跳跃，但钷素不足")

        elif travel_method == "slow_travel":
            # 计算距离
            if isinstance(player.fleet.location, str):
                # 如果舰队在星球上，使用星球 ID 计算距离
                current_world = self.game.world_manager.get_world_by_id(player.fleet.location)
                if not current_world:
                    return
                start_location = (current_world.x, current_world.y, current_world.z)
            else:
                start_location = player.fleet.location
            distance = self.calculate_distance(start_location, destination)
            # cost = self.calculate_slow_travel_cost(distance) #移除
            action_points_cost = int(distance * self.ACTION_POINTS_PER_DISTANCE)  # 计算行动点消耗
            if player.action_points >= action_points_cost: # 检查行动点
                # 发送允许移动消息, 扣除行动点
                player.action_points -= action_points_cost
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_ALLOWED, {
                    "player_id": player.player_id,
                    "destination": destination,
                    "travel_method": travel_method,
                    # "cost": cost, #移除
                }, self)
            else:
                self.game.log.warn(f"玩家 {player.player_id} 尝试缓慢航行，但行动点不足")

    # def update_fleet_positions(self): #移除

    def handle_fleet_movement_interrupt(self, message: Message): #修改
        """处理舰队移动中断请求"""
        # player_id = message.data["player_id"] #修改
        # player = self.game.player_manager.get_player_by_id(player_id)
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        # 中断移动：清除目标，并将位置设置为当前坐标 (如果不在星球上)
        if isinstance(player.fleet.location, tuple):  # 如果已经在移动中
            # player.fleet.location = player.fleet.location #保持不变
            pass
        else: #如果还在星球上,则保持不动
             pass
        player.fleet.destination = None
        player.fleet.travel_method = None
        
    def calculate_distance(self, coord1, coord2):
        """计算两个坐标之间的距离"""
        dx = coord1[0] - coord2[0]
        dy = coord1[1] - coord2[1]
        dz = coord1[2] - coord2[2]
        return (dx**2 + dy**2 + dz**2)**0.5

    def check_fleet_proximity(self):
        """检查每个玩家的舰队是否靠近星球或其他可交互对象, 并且发送抵达事件"""
        for player in self.game.player_manager.players.values():
            # 如果舰队已经在星球上，或者正在跃迁，或者正在移动中，则跳过
            if (player.fleet.landed_on is not None) or (player.fleet.travel_method == "subspace_jump") or (player.fleet.travel_method == "slow_travel") :
                continue

            for world in self.game.world_manager.world_instances.values():
                distance = self.calculate_distance(player.fleet.location, (world.x, world.y, world.z))
                if distance <= player.fleet.travel_speed:
                    # 触发到达事件
                    self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                        "player_id": player.player_id,
                        "location": (world.x, world.y, world.z),  # 发送星球坐标
                    }, self)