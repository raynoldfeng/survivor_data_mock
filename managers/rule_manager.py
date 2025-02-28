# managers/rule_manager.py
from typing import Dict, List, Tuple, Any
from message_bus import MessageBus, MessageType
from game import Game

class RulesManager:
    _instance = None

    SUBSPACE_JUMP_COST = 10
    SLOW_TRAVEL_COST = 1  # 每回合消耗
    SLOW_TRAVEL_MAX_DISTANCE = 10.0
    # SLOW_TRAVEL_DURATION = 3  # 不再需要固定时长

    def __new__(cls, game: Game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.rule_manager = cls._instance
        return cls._instance

    def tick(self):
        #统一监听 FLEET_MOVE_REQUEST
        for message in MessageBus.get_messages(type=MessageType.FLEET_MOVE_REQUEST):
            self.handle_fleet_move_request(message)
        # 新增：监听移动中断消息
        for message in MessageBus.get_messages(type=MessageType.FLEET_MOVEMENT_INTERRUPT):
            self.handle_fleet_movement_interrupt(message)
        self.update_fleet_positions()
        self.check_fleet_proximity()  # 新增：检查舰队邻近

    def handle_fleet_move_request(self, message: "Message"):
        """处理舰队移动请求 (由 PlayerManager 发送)"""
        player_id = message.data["player_id"]
        destination = message.data["destination"]  # 现在 destination 直接是坐标
        travel_method = message.data["travel_method"]  # 获取移动方式
        player = self.game.player_manager.get_player_by_id(player_id)

        if not player:
            return

        if travel_method == "subspace_jump":
            self.apply_subspace_jump_rule(player_id, destination)
        elif travel_method == "slow_travel":
            self.apply_slow_travel_rule(player_id, destination)

    def apply_subspace_jump_rule(self, player_id, destination):
        """处理亚空间跳跃规则"""
        player = self.game.player_manager.get_player_by_id(player_id)

        if player.get_resource_amount("promethium") >= self.SUBSPACE_JUMP_COST:
            # 扣除资源, 通过发送消息
            MessageBus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                "target_id": player_id,
                "target_type": "Player",
                "resource_id": "resource.promethium",
                "modifier": "REDUCE",
                "quantity": self.SUBSPACE_JUMP_COST,
                "duration": 0,
            }, self)

            # 发送舰队移动消息 (由 PlayerManager 处理)
            MessageBus.post_message(MessageType.FLEET_MOVE_REQUEST, {
                "player_id": player_id,
                "location": destination,  # 直接设置为目标坐标
                "destination": None,
                "travel_method": "subspace_jump",
            }, self)
             # 触发到达事件
            MessageBus.post_message(MessageType.FLEET_ARRIVE, { #消息类型修改
                "player_id": player_id,
                "location": destination, #现在统一是坐标
            }, self)
        else:
            self.game.log.warn(f"玩家 {player_id} 尝试亚空间跳跃，但钷素不足")

    def apply_slow_travel_rule(self, player_id, destination):
        """处理缓慢航行规则"""
        player = self.game.player_manager.get_player_by_id(player_id)
        # 首次移动，需要判断最大距离
        if  isinstance(player.fleet.location, str):
            current_world_id = player.fleet.location
            current_world = self.game.world_manager.get_world_by_id(current_world_id)
            if not current_world:
                return
            start_location = (current_world.x, current_world.y, current_world.z)
            distance = self.calculate_distance(start_location, destination)
            if distance > self.SLOW_TRAVEL_MAX_DISTANCE:
                self.game.log.warn(f"玩家 {player_id} 尝试缓慢航行，但距离太远")
                return
            # 发送舰队移动消息 (由 PlayerManager 处理)
            MessageBus.post_message(MessageType.FLEET_MOVE_REQUEST, {
                "player_id": player_id,
                "location": start_location,  # 设置为起始坐标
                "destination": destination,
                "travel_start_round": self.game.current_round,
                "travel_method": "slow_travel",
            }, self)
            return
        # 持续移动，扣除资源, 通过发送消息
        MessageBus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
            "target_id": player_id,
            "target_type": "Player",
            "resource_id": "promethium",
            "modifier": "REDUCE",
            "quantity": self.SLOW_TRAVEL_COST,
            "duration": 0,
        }, self)

    def update_fleet_positions(self):
        """更新所有正在星际移动的舰队的位置"""
        for player in self.game.player_manager.players.values():
            if player.fleet.destination and isinstance(player.fleet.location, tuple):  # 舰队正在移动中
                # 获取目标坐标
                target_location = player.fleet.destination

                # 计算移动向量
                dx = target_location[0] - player.fleet.location[0]
                dy = target_location[1] - player.fleet.location[1]
                dz = target_location[2] - player.fleet.location[2]
                distance = (dx**2 + dy**2 + dz**2)**0.5

                if distance <= player.fleet.travel_speed:
                    # 舰队到达目的地,发送移动消息和到达消息
                    MessageBus.post_message(MessageType.FLEET_MOVE_REQUEST, {
                        "player_id": player.player_id,
                        "location": player.fleet.destination,
                        "destination": None,
                        "travel_method": "slow_travel",
                    }, self)
                    MessageBus.post_message(MessageType.FLEET_ARRIVE, { #消息类型修改
                        "player_id": player.player_id,
                        "location": player.fleet.destination,  # 目标坐标
                    }, self)

                else:
                    # 更新舰队位置 (按比例移动)
                    ratio = player.fleet.travel_speed / distance
                    new_x = player.fleet.location[0] + dx * ratio
                    new_y = player.fleet.location[1] + dy * ratio
                    new_z = player.fleet.location[2] + dz * ratio
                    # 发送 FLEET_MOVE_REQUEST 消息，更新位置
                    MessageBus.post_message(MessageType.FLEET_MOVE_REQUEST, {
                        "player_id": player.player_id,
                        "location": (new_x, new_y, new_z),
                        "destination": player.fleet.destination,
                        "travel_method": "slow_travel",
                    }, self)

    def handle_fleet_movement_interrupt(self, message: "Message"):
        """处理舰队移动中断请求"""
        player_id = message.data["player_id"]
        player = self.game.player_manager.get_player_by_id(player_id)

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
            # 如果舰队已经在星球上，或者正在跃迁，则跳过
            if isinstance(player.fleet.location, str) or player.fleet.travel_method == "subspace_jump":
                continue

            for world in self.game.world_manager.world_instances.values():
                distance = self.calculate_distance(player.fleet.location, (world.x, world.y, world.z))
                if distance <= player.fleet.travel_speed:
                    # 触发到达事件 (即使已经在移动中)
                    MessageBus.post_message(MessageType.FLEET_ARRIVE, {
                        "player_id": player.player_id,
                        "location": (world.x, world.y, world.z),  # 发送星球坐标
                    }, self)