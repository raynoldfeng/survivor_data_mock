from typing import Tuple
from .message_bus import MessageType, Message

class RulesManager:
    _instance = None

    SUBSPACE_JUMP_COST = 10  # 假设的跃迁消耗
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
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_LAND_REQUEST, cls._instance.handle_fleet_land_request)  # 改为 REQUEST
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_TAKEOFF_REQUEST, cls._instance.handle_fleet_takeoff_request) # 新增
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_EXPLORE_WORLD_REQUEST, cls._instance.handle_explore_world_request)

        return cls._instance

    def tick(self, tick_counter):
        if tick_counter % self.tick_interval == 0:
            # 1. 处理碰撞检测 (移动到 RuleManager)
            self.check_collisions()

            # 2. 处理舰队移动
            for player_id, player in self.game.player_manager.players.items():
                self.move_fleet(player_id)

    def check_collisions(self):
        """检查所有玩家舰队与星球的碰撞"""
        for player_id, player in self.game.player_manager.players.items():
            fleet = player.fleet
            if fleet.location:
                for world in self.game.world_manager.world_instances.values():
                    if world.check_collision(fleet.location):
                        self.game.message_bus.post_message(MessageType.INTERSECTION_EVENT, {
                            "location": fleet.location,
                            "objects": [player_id, world.object_id],
                        }, self)
                        break  # 假设一个舰队同时只能与一个星球碰撞

    def handle_fleet_move_request(self, message: Message):
        """处理舰队移动请求, 只需要处理跃迁的资源消耗"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        travel_method = message.data["travel_method"]

        if not player:
            return

        if travel_method == "subspace_jump":
            if player.get_resource_amount("promethium") >= self.SUBSPACE_JUMP_COST:
                # 发送修改资源的消息 (扣除钷素)
                self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                    "target_id": player.player_id,
                    "target_type": "Player",
                    "resource_id": "promethium",
                    "modifier": Modifier.REDUCE,
                    "quantity": self.SUBSPACE_JUMP_COST,
                    "duration": 0,
                }, self)
            else:
                self.game.log.warn(f"玩家 {player.player_id} 尝试亚空间跳跃，但钷素不足")

    def handle_fleet_movement_interrupt(self, message: Message):
        """处理舰队移动中断"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        player.fleet.dest = None  # 清空目标
        player.fleet.path = None  # 清空路径
        player.fleet.travel_method = None  # 清空移动方式

    def is_valid_move(self, player_id: str, new_location: Tuple[int, int, int]) -> bool:
        """检查移动是否合法 (新位置是否在星球的不可穿透区域内)"""
        player = self.game.player_manager.get_player_by_id(player_id)
        if not player:
            return False

        # 检查新位置是否与其他物体碰撞 (包括星球的不可穿透区域)
        for world in self.game.world_manager.world_instances.values():
            if world.check_collision(new_location) and world.impenetrable_half_extent >= world.calculate_distance_to_center(new_location):
                # 停止移动
                player.fleet.dest = None
                player.fleet.path = None
                # 发送 FLEET_MOVEMENT_INTERRUPTED 消息
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, {
                    "player_id": player_id,
                }, self)
                return False  # 不合法

        return True  # 合法

    def handle_explore_world_request(self, message: Message):
        """处理探索星球的请求"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        world_id = message.data["world_id"]
        world = self.game.world_manager.get_world_by_id(world_id)

        if not player or not world:
            return

        # 检查是否已经探索过
        if world_id in player.explored_planets:
            self.game.log.info(f"玩家 {player.player_id} 已经探索过星球 {world_id}。")
            return

        # 检查是否已降落
        if player.fleet.landed_on != world_id:
            self.game.log.info(f"玩家 {player.player_id} 的舰队未降落在星球 {world_id} 上，无法探索。")
            return

        # 标记为已探索
        player.explored_planets.append(world_id)
        self.game.log.info(f"玩家 {player.player_id} 成功探索星球 {world_id}！")

        # 计算并应用探索奖励
        for reward in world.exploration_rewards:
            resource_id, quantity = reward
            self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                "target_id": player.player_id,
                "target_type": "Player",
                "resource_id": resource_id,
                "modifier": "INCREASE",
                "quantity": quantity,
                "duration": 0,  # 立即生效
            }, self)
    def handle_fleet_land_request(self, message: Message):
        """处理降落请求, 检查舰队当前位置是否在星球表面"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        world_id = message.data["world_id"]
        world = self.game.world_manager.get_world_by_id(world_id)
        if not world:
            return

        # 检查舰队当前位置是否在星球表面 (保持使用 is_on_surface)
        if world.is_on_surface(player.fleet.location):
            # 标记玩家舰队已经降落
            player.fleet.landed_on = world.object_id
            # 添加到星球的 docked_fleets
            if world.object_id not in world.docked_fleets:
                world.docked_fleets[player.player_id] = player.fleet.location
            self.game.log.info(f"玩家 {message.data['player_id']} 的舰队降落在星球 {world.world_config.world_id}！")
        else:
            self.game.log.warn(f"玩家 {message.data['player_id']} 的舰队未到达星球 {world_id} 表面，无法降落。")
        pass

    def handle_fleet_takeoff_request(self, message: Message):
        """处理起飞请求"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        # 检查是否已经降落
        if player.fleet.landed_on is None:
            self.game.log.warn(f"玩家 {player.player_id} 的舰队未降落，无法起飞。")
            return

        world = self.game.world_manager.get_world_by_id(player.fleet.landed_on)
        if not world:
            return

        # 从星球的 docked_fleets 中移除
        if player.player_id in world.docked_fleets:
            del world.docked_fleets[player.player_id]

        # 取消降落状态
        player.fleet.landed_on = None
        self.game.log.info(f"玩家 {player.player_id} 的舰队从星球起飞！")

    def move_fleet(self, player_id: str):
        """移动舰队 (每个 tick 调用)"""
        player = self.game.player_manager.get_player_by_id(player_id)
        if not player:
            return

        fleet = player.fleet

        # 航行规则：
        # 1. slow_travel (慢速旅行):
        #    - 如果 path 不为空，则沿着 path 移动。
        #    - 如果 path 为空：
        #      - 如果 dest 不为空，则表示已经到达目标星球边缘 或 无法移动（寻路失败/中断/目标不可达）。
        #      - 如果 dest 为空，则表示没有移动目标。
        # 2. subspace_jump (亚空间跳跃):
        #    - 直接跃迁到 dest 指定的坐标。
        #    - 如果 dest 是星球ID，则跃迁到星球边缘的某个坐标。（Robot.think() 中保证）
        #    - 跃迁完成后，dest 和 travel_method 都会被清空。
        # 3. 碰撞检测：
        #    - 在每次移动前，都会检查新位置是否合法（is_valid_move()）。
        #    - 如果新位置位于星球的不可穿透区域内，则移动会被中断，path 和 dest 会被清空。
        # 4. 到达目标：
        #    - slow_travel 到达星球边缘：path 会变为空列表，但 dest 仍然是星球ID，此时可以触发降落逻辑。
        #    - slow_travel 到达坐标：path 会变为空列表，dest 是坐标。
        #    - subspace_jump 到达星球边缘/坐标：dest 会被设置为星球边缘/坐标，path 为空。

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
                # 记录移动日志
                self.game.log.info(f"玩家 {player_id} 的舰队慢速移动至 {fleet.location}")
                # 判断是否到达最终目标 (path 为空)
                if not fleet.path:
                    if fleet.dest:
                        # 检查 dest 是星球 ID 还是坐标, 这里发送到达事件
                        world = self.game.world_manager.get_world_by_id(fleet.dest)
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
                player.fleet.dest = None
                player.fleet.path = None
                # 发送 FLEET_MOVEMENT_INTERRUPTED 消息
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, {
                    "player_id": player_id,
                }, self)

        # 情况 2: 跃迁
        elif fleet.travel_method == "subspace_jump":
            destination_coordinate = fleet.dest

            if self.is_valid_move(player_id, destination_coordinate):
                # 更新位置
                self.game.world_manager.update_object_location(
                    player_id, fleet.location, destination_coordinate
                )
                fleet.location = destination_coordinate
                # 直接发送到达消息, 根据dest类型判断, 如果是星球, 则发送world类型的到达消息, world_id
                world = self.game.world_manager.get_world_by_id(fleet.dest)
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                        "player_id": player_id,
                        "location": fleet.location,
                        "arrival_type": "coordinate" if not world else "world",
                        "world_id": world.object_id if world else None # 如果是星球，则提供id
                    }, self)
                # 清空状态
                fleet.dest = None
                fleet.travel_method = None
                # 记录移动日志
                self.game.log.info(f"玩家 {player_id} 的舰队跃迁至 {fleet.location}")
            else:
                #停止移动
                player.fleet.dest = None
                player.fleet.path = None
                # 发送 FLEET_MOVEMENT_INTERRUPTED 消息
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, {
                    "player_id": player_id,
                }, self)
        elif fleet.path is None or len(fleet.path) == 0: # 检查path是否为空
            if fleet.dest:
                # 1. 刚刚完成 subspace_jump 或 slow_travel
                # 2. 或者寻路失败/路径中断
                # 3. 到达星球的不可穿透区域
                self.game.log.info(f"玩家 {player_id} 的舰队 path 为空, 但有 dest: {fleet.dest}")
                # 在这里可以添加额外的处理逻辑，例如：
                # - 尝试重新寻路 (如果距离目标还很远)
                # - 如果已经非常接近目标（例如，在 final_destination 的几个单元格内），
                #   可以考虑直接“着陆”到目标星球上（如果 final_destination 是星球）
                # - 什么都不做，等待下一 tick

                # 简单起见，我们先什么都不做
                pass