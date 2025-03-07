from typing import Dict, List, Tuple, Any
from .message_bus import MessageType, Message

class RulesManager:
    _instance = None

    SUBSPACE_JUMP_COST = 10
    ACTION_POINTS_PER_DISTANCE = 1

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.rule_manager = cls._instance
            cls._instance.tick_interval = 1
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVE_REQUEST, cls._instance.handle_fleet_move_request)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, cls._instance.handle_fleet_movement_interrupt)
            # 移动到这里的订阅
            # cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_ARRIVE, cls._instance.handle_arrival) #移除
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_LAND, cls._instance.handle_land)
        return cls._instance

    def tick(self, tick_counter):
        if tick_counter % self.tick_interval == 0:
            # self.check_fleet_proximity() #移除
            self.check_collisions()
            # 在tick里处理移动
            for player_id, player in self.game.player_manager.players.items():
                self.move_fleet(player_id)

    def handle_fleet_move_request(self, message: Message):
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        destination = message.data["destination"]
        travel_method = message.data["travel_method"]

        if not player:
            return

        # 检查是否是重复移动指令
        if travel_method == "slow_travel" and player.fleet.final_destination == destination:
            self.game.log.info(f"玩家 {player.player_id} 已经朝这个目标移动")
            return
        # if travel_method == "subspace_jump" and player.fleet.location == destination: #这种情况会在慢速旅行的逻辑中处理
        #     self.game.log.info(f"玩家 {player.player_id} 已经跃迁至目标位置")
        #     return

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

                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_ALLOWED, {
                    "player_id": player.player_id,
                    "destination": destination,
                    "travel_method": travel_method,
                }, self)
            else:
                self.game.log.warn(f"玩家 {player.player_id} 尝试亚空间跳跃，但钷素不足")

        elif travel_method == "slow_travel":
            # 更新舰队状态 (在PlayerManager中处理)
            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_ALLOWED, {
                "player_id": player.player_id,
                "destination": destination,
                "travel_method": travel_method,
            }, self)

    def handle_fleet_movement_interrupt(self, message: Message):
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        player.fleet.final_destination = None
        player.fleet.path = None
        player.fleet.travel_method = None

    def is_valid_move(self, player_id: str, new_location: Tuple[int, int, int]) -> bool:
        """检查移动是否合法"""
        player = self.game.player_manager.get_player_by_id(player_id)
        if not player:
            return False

        # 检查新位置是否在不可穿透半径内
        if not self.game.world_manager.is_location_available(new_location):
            # 停止移动
            player.fleet.final_destination = None
            player.fleet.path = None
            # 发送 FLEET_MOVEMENT_INTERRUPTED 消息
            self.game.message_bus.post_message(MessageType.FLEET_MOVEMENT_INTERRUPTED, {
                "player_id": player_id,
            }, self)
            return False  # 不合法
        return True  # 合法

    def check_collisions(self):
        """检测所有舰队的碰撞"""
        for player_id, player in self.game.player_manager.players.items():
            fleet = player.fleet
            if fleet.location:  # 确保舰队有位置信息
                location = fleet.location
                # 检查舰队所在 cell 是否被星球占用 (impenetrable_half_extent)
                for world in self.game.world_manager.world_instances.values():
                    distance_x = abs(location[0] - world.location[0])
                    distance_y = abs(location[1] - world.location[1])
                    distance_z = abs(location[2] - world.location[2])
                    # 只要舰队和星球中心距离在"impenetrable_half_extent + 1"范围内, 就判定为碰撞
                    if (
                        distance_x <= world.impenetrable_half_extent + 1 and
                        distance_y <= world.impenetrable_half_extent + 1 and
                        distance_z <= world.impenetrable_half_extent + 1 and
                        (
                            distance_x == world.impenetrable_half_extent + 1 or
                            distance_y == world.impenetrable_half_extent + 1 or
                            distance_z == world.impenetrable_half_extent + 1
                        )
                    ):
                        self.game.log.error(f"舰队 {player_id} 与星球 {world.world_config.world_id} 发生碰撞！")
                        # TODO: 在这里添加碰撞处理逻辑 (例如，舰队损毁、触发事件等)
                        # 发送碰撞事件
                        self.game.message_bus.post_message(MessageType.INTERSECTION_EVENT, {
                            "location": location,
                            "objects": [player_id, world.object_id],
                        }, self)
                        break  # 假设一个舰队同时只能与一个星球碰撞

    def handle_land(self, message: Message):
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        world_id = message.data["world_id"]
        world = self.game.world_manager.get_world_by_id(world_id)

        if not world:
            return
        # 标记玩家舰队已经降落
        player.fleet.landed_on = world.object_id
        self.game.log.info(f"玩家 {message.data['player_id']} 的舰队降落在星球 {world.world_config.world_id}！")
        pass

    def move_fleet(self, player_id: str):
        """移动舰队 (每个 tick 调用)"""
        player = self.game.player_manager.get_player_by_id(player_id)
        if not player:
            return

        fleet = player.fleet

        # 情况 1 & 3: 慢速旅行
        if fleet.path and len(fleet.path) > 0:  # 检查 path 是否为空
            next_location = fleet.path[0]  # 获取下一个目标位置
            # 移动到当前寻路目标 (直接使用 cell 坐标)
            if self.is_valid_move(player_id, next_location):
                # 更新位置
                self.game.world_manager.update_object_location(
                    player_id, fleet.location, next_location
                )
                fleet.location = next_location
                # 移动到下一个 cell
                fleet.move_to_next_cell()  # 这会更新 fleet.path
                # 判断是否到达最终目标 (path 为空)
                if not fleet.path:
                    if fleet.final_destination:
                        # 检查 final_destination 是星球 ID 还是坐标
                        world = self.game.world_manager.get_world_by_id(fleet.final_destination)
                        if world:
                            # 到达星球
                            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                                "player_id": player_id,
                                "location":  fleet.location,
                                "arrival_type": "world",  # 明确到达类型
                                "world_id": world.object_id,
                            }, self)
                        else:
                            # 到达坐标
                            self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                                "player_id": player_id,
                                "location": fleet.location,
                                "arrival_type": "coordinate",  # 普通坐标
                            }, self)
            else:
                # 停止移动
                player.fleet.final_destination = None
                player.fleet.path = None
                # 发送 FLEET_MOVEMENT_INTERRUPTED 消息
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, {
                    "player_id": player_id,
                }, self)

        # 情况 2: 跃迁
        elif fleet.travel_method == "subspace_jump":  # 没有在寻路，但是是跃迁
            #尝试获取最终目标坐标, 因为前面已经保证了destination是坐标, 这里直接用
            destination_coordinate = fleet.final_destination
            if self.is_valid_move(player_id, destination_coordinate):
                # 更新位置
                self.game.world_manager.update_object_location(
                    player_id, fleet.location, destination_coordinate
                )
                fleet.location = destination_coordinate
                # 直接发送到达消息
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                        "player_id": player_id,
                        "location": fleet.location,
                        "arrival_type": "coordinate",  # 跃迁的目标一定是坐标
                    }, self)
                # 清空状态
                fleet.final_destination = None
                fleet.travel_method = None
            else:
                #停止移动
                player.fleet.final_destination = None
                player.fleet.path = None
                # 发送 FLEET_MOVEMENT_INTERRUPTED 消息
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, {
                    "player_id": player_id,
                }, self)