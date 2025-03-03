from typing import Dict, List, Tuple, Any
from .message_bus import MessageType, Message

class RulesManager:
    _instance = None

    SUBSPACE_JUMP_COST = 10
    # SLOW_TRAVEL_MAX_DISTANCE = 10.0  # 可以保留，用于限制单次缓慢航行的最大距离
    ACTION_POINTS_PER_DISTANCE = 1  # 每单位距离消耗的行动点数 (根据需要调整)

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.rule_manager = cls._instance
            cls._instance.tick_interval = 1  # 每分钟tick一次 (根据您的基本tick间隔设置)
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVE_REQUEST, cls._instance.handle_fleet_move_request)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, cls._instance.handle_fleet_movement_interrupt)
        return cls._instance

    def tick(self, tick_counter):
        if tick_counter % self.tick_interval == 0:
            self.check_fleet_proximity()

    def handle_fleet_move_request(self, message: Message):
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        destination = message.data["destination"]
        travel_method = message.data["travel_method"]

        if not player:
            return

        # 检查是否是重复移动指令
        if travel_method == "slow_travel" and player.fleet.destination == destination:
            self.game.log.info(f"玩家 {player.player_id} 已经朝这个目标移动")
            return
        if travel_method == "subspace_jump" and player.fleet.location == destination:
            self.game.log.info(f"玩家 {player.player_id} 已经跃迁至目标位置")
            return

        if travel_method == "subspace_jump":
            if player.get_resource_amount("promethium") >= self.SUBSPACE_JUMP_COST:
                # 发送修改资源的消息 (扣除钷素)
                self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                    "target_id": player.player_id,
                    "target_type": "Player",
                    "resource_id": "promethium",
                    "modifier": "REDUCE",
                    "quantity": self.SUBSPACE_JUMP_COST,
                    "duration": 0,
                }, self)

                # 更新舰队状态 (在PlayerManager中处理)
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_ALLOWED, { # 还是需要这个消息
                    "player_id": player.player_id,
                    "destination": destination,
                    "travel_method": travel_method,
                }, self)
            else:
                self.game.log.warn(f"玩家 {player.player_id} 尝试亚空间跳跃，但钷素不足")

        elif travel_method == "slow_travel":
            if isinstance(player.fleet.location, str):
                current_world = self.game.world_manager.get_world_by_id(player.fleet.location)
                if not current_world:
                    return
                start_location = (current_world.x, current_world.y, current_world.z)
            else:
                start_location = player.fleet.location
            distance = self.calculate_distance(start_location, destination)
            action_points_cost = int(distance * self.ACTION_POINTS_PER_DISTANCE)
            if player.action_points >= action_points_cost:
                # 发送修改资源的消息 (扣除行动点)
                self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                    "target_id": player.player_id,
                    "target_type": "Player",
                    "resource_id": "action_points",  # 修改资源类型为行动点
                    "modifier": "REDUCE",
                    "quantity": action_points_cost,
                    "duration": 0,
                }, self)

                # 更新舰队状态 (在PlayerManager中处理)
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_ALLOWED, { # 还是需要这个消息
                    "player_id": player.player_id,
                    "destination": destination,
                    "travel_method": travel_method,
                }, self)
            else:
                self.game.log.warn(f"玩家 {player.player_id} 尝试缓慢航行，但行动点不足")

    def handle_fleet_movement_interrupt(self, message: Message):
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        # 中断移动：清除目标，并将位置设置为当前坐标 (如果不在星球上)
        if isinstance(player.fleet.location, tuple):  # 如果已经在移动中
            pass
        else:  # 如果还在星球上,则保持不动
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
            if (player.fleet.landed_on is not None) or (player.fleet.travel_method == "subspace_jump"):
                continue

            # 如果是缓慢航行到达目的地，也触发到达事件
            if player.fleet.travel_method == "slow_travel" and player.fleet.location == player.fleet.destination:
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                    "player_id": player.player_id,
                    "location": player.fleet.location,
                    "arrival_type": "slow_travel",  # 新增 arrival_type
                }, self)
                continue

            # 检测是否靠近星球
            for world in self.game.world_manager.world_instances.values():
                distance = self.calculate_distance(player.fleet.location, (world.x, world.y, world.z))
                if distance <= player.fleet.travel_speed:
                    self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                        "player_id": player.player_id,
                        "location": (world.x, world.y, world.z),
                        "arrival_type": "proximity",  # 新增 arrival_type
                    }, self)