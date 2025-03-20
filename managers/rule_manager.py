from basic_types.base_object import BaseObject
from basic_types.basic_typs import Vector3
from basic_types.modifier import ModifierConfig
from basic_types.resource import Resource
from common import *
from basic_types.enums import *
from .message_bus import MessageType, Message
import datetime


class RulesManager(BaseObject):
    _instance = None

    SUBSPACE_JUMP_COST = 10  # 假设的跃迁消耗
    ACTION_POINTS_PER_DISTANCE = 1

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.rule_manager = cls._instance
            cls._instance.fleet_spacetime = {}

            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVE_REQUEST, cls._instance.handle_fleet_move_request)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, cls._instance.handle_fleet_movement_interrupt)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_LAND_REQUEST, cls._instance.handle_fleet_land_request)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_TAKEOFF_REQUEST, cls._instance.handle_fleet_takeoff_request)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_EXPLORE_WORLD_REQUEST, cls._instance.handle_explore_world_request)

        return cls._instance

    def tick(self):
        # 1. 处理碰撞检测
        self.check_collisions()

        # 2. 处理舰队移动
        for player_id, player in self.game.player_manager.players.items():
            self.move_fleet(player_id)

    def check_collisions(self):
        """检查所有玩家舰队与星球的碰撞 (包括不可穿透区域)，以及舰队之间的碰撞"""
        for player_id, player in self.game.player_manager.players.items():
            fleet = player.fleet
            if fleet.location:
                # 检查是否与星球的不可穿透部分碰撞
                if self.game.world_manager.is_impenetrable(fleet.location):
                    world_id = self.game.world_manager.impenetrable_locations.get(fleet.location)
                    # 触发坠毁逻辑 (这里只是发送一个消息)
                    self.game.message_bus.post_message(MessageType.INTERSECTION_EVENT, {
                        "location": fleet.location,
                        "objects": [player_id, world_id],  # 坠毁只涉及舰队和星球
                        "crash": True  # 添加一个标志，表示坠毁
                    }, self)
                    # 可以在这里添加其他处理逻辑，例如：
                    # - 扣除舰队的耐久度
                    # - 将舰队从游戏中移除
                    # - ...
                    continue  # 发生碰撞后，跳过后续的舰队间碰撞检查

                # 检查舰队之间的碰撞
                for other_player_id, other_player in self.game.player_manager.players.items():
                    if player_id != other_player_id:  # 排除自己
                        other_fleet = other_player.fleet
                        if fleet.location == other_fleet.location:
                            self.game.message_bus.post_message(MessageType.INTERSECTION_EVENT, {
                                "location": fleet.location,
                                "objects": [player_id, other_player_id],  # 所有相交的舰队 ID
                                "crash": False  # 不会坠毁
                            }, self)

    def handle_fleet_move_request(self, message: Message):
        """处理舰队移动请求, 只需要处理跃迁的资源消耗"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        travel_method = message.data["travel_method"]
        path = message.data["path"]

        player.fleet.set_travel_method(travel_method)
        if not player:
            return

        if travel_method == TravelMethod.SUBSPACEJUMP:
            # 亚空间跳跃情况下只能跳一次，如果有多个路径的话给予抹除？
            player.set_path(path[:1])
            if player.get_resource_amount("promethium") >= self.SUBSPACE_JUMP_COST:
                # 发送修改资源的消息 (扣除钷素)
                modifier_config = ModifierConfig(ObjectType.PLAYER, Resource.get_resource_by_id("resource.promethium"), ModifierType.LOSS, self.SUBSPACE_JUMP_COST, 0, 0)
                self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE_REQUEST, {
                    "target_id": player.object_id,
                    "modifier_config": modifier_config
                }, self)
            else:
                self.game.log.warn(f"玩家 {player.object_id} 尝试亚空间跳跃，但钷素不足")
        else:
            player.fleet.set_path(path)
            pass

    def handle_fleet_movement_interrupt(self, message: Message):
        """处理舰队移动中断"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        player.fleet.set_path([])

    def is_reachable(self, new_location: Vector3) -> bool:
        """检查移动是否合法 (新位置是否在星球的不可穿透区域内, 以及是否格子相连)"""
        # 检查新位置是否与其他物体碰撞 (包括星球的不可穿透区域)
        if self.game.world_manager.is_impenetrable(new_location):
            # 停止移动
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
            self.game.log.info(f"玩家 {player.object_id} 已经探索过星球 {world_id}。")
            return

        # 检查是否已降落
        if player.fleet.landed_on != world_id:
            self.game.log.info(f"玩家 {player.object_id} 的舰队未降落在星球 {world_id} 上，无法探索。")
            return

        # 标记为已探索
        player.explored_planets.append(world_id)
        self.game.log.info(f"玩家 {player.object_id} 成功探索星球 {world_id}！")
        world.owner = player.object_id

        # 计算并应用探索奖励
        for reward in world.exploration_rewards:
            resource_id, quantity = reward
            # 获取资源配置
            resource = Resource.get_resource_by_id(resource_id)
            if not resource:
                self.game.log.error(f"无效的资源ID: {resource_id}")
                continue

            # 创建奖励修正
            modifier_config = ModifierConfig(
                target_type=ObjectType.PLAYER,
                data_type=resource.id,
                modifier_type=ModifierType.GAIN,
                quantity=quantity,
                duration=0,
                delay=0
            )

            # 发送奖励消息
            self.game.message_bus.post_message(
                MessageType.MODIFIER_APPLY_REQUEST,
                {
                    "target_id": player.object_id,
                    "modifier_config": modifier_config
                },
                self
            )
            self.game.log.info(f"应用探索奖励: {quantity} {resource.name_id}")

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
            player.fleet.set_path([])
            # 添加到星球的 docked_fleets
            if world.object_id not in world.docked_fleets:
                world.docked_fleets[player.object_id] = player.fleet.location
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
            self.game.log.warn(f"玩家 {player.object_id} 的舰队未降落，无法起飞。")
            return

        world = self.game.world_manager.get_world_by_id(player.fleet.landed_on)
        if not world:
            return

        # 从星球的 docked_fleets 中移除
        if player.object_id in world.docked_fleets:
            del world.docked_fleets[player.object_id]

        # 取消降落状态
        player.fleet.landed_on = None
        player.fleet.set_path([])
        self.game.log.info(f"玩家 {player.object_id} 的舰队从星球起飞！")

    def move_fleet(self, player_id: str):
        """移动舰队 (每个 tick 调用)"""
        player = self.game.player_manager.get_player_by_id(player_id)
        if not player:
            return

        fleet = player.fleet
        if not fleet.path:
            return

        now = datetime.datetime.now()
        current_location = fleet.location

        # 处理不同移动方式
        move_success = False
        steps = 0
        if fleet.travel_method == TravelMethod.SUBSPACEJUMP:
            # 跃迁移动，仅验证合法性
            next_location = fleet.path[0]
            move_success = self._handle_subspace_jump(player, next_location)
        elif fleet.travel_method == TravelMethod.SLOWTRAVEL:
            # 慢旅行移动
            move_success, steps = self._handle_slow_travel(player, now)

        if move_success:
            self.game.log.info(f"玩家 {player_id} 通过{steps}步, 从{current_location} 移动至 {fleet.location}")

            # 检查是否到达终点
            if not fleet.path:
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_ARRIVE, {
                    "player_id": player_id,
                    "location": fleet.location,
                    "arrival_type": "coordinate",
                }, self)

    def _handle_subspace_jump(self, player, next_location):
        """处理亚空间跳跃，仅验证合法性"""
        # 验证跳跃合法性
        if not self.is_reachable(next_location):
            return False
        return True

    def _handle_slow_travel(self, player, now):
        """处理慢旅行移动"""
        fleet = player.fleet
        current_location = fleet.location
        player_id = player.object_id

        # 计算时间差
        if player_id not in self.fleet_spacetime:
            self.fleet_spacetime[player_id] = (current_location, now)
        last_move_time = self.fleet_spacetime.get(player_id, (None, now))[1]
        time_elapsed = (now - last_move_time).seconds

        # 计算可移动的步数
        steps_possible = int(time_elapsed * fleet.travel_speed)
        actual_steps = 0

        if steps_possible <= 0:
            return False, 0
        
        for _ in range(steps_possible):
            actual_steps += 1
            if not fleet.path:
                break

            next_location = fleet.path[0]
            if not self._is_single_step_valid(current_location, next_location):
                # 移动失败处理
                self.game.message_bus.post_message(MessageType.PLAYER_FLEET_MOVEMENT_INTERRUPT, {
                    "player_id": player_id,
                }, self)
                return False, actual_steps 

            current_location = next_location
            fleet.move_to_next_cell()
            self.fleet_spacetime[player_id] = (current_location, now)

        return True, actual_steps

    def _is_single_step_valid(self, loc1: Vector3, loc2: Vector3) -> bool:
        """检查单步移动是否合法（在接触面且可达）"""
        return (self.is_reachable(loc2) # 可到达
                and self.is_contiguous(loc1, loc2) #连续
                or loc1 == loc2 )# 没动也算

    def is_contiguous(self, loc1: Vector3, loc2: Vector3) -> bool:
        """检查两个位置是否在接触面（相邻）"""
        dx = abs(loc1.x - loc2.x)
        dy = abs(loc1.y - loc2.y)
        dz = abs(loc1.z - loc2.z)
        return (dx + dy + dz) == 1