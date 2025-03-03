from typing import Dict
from .message_bus import MessageType, Message  # 导入 Message

class InteractionManager:
    _instance = None

    def __new__(cls, game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.interaction_manager = cls._instance
            cls._instance.tick_interval = 1 # 可以设置为你想要的.
            # 订阅消息
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_ARRIVE, cls._instance.handle_arrival)
            cls._instance.game.message_bus.subscribe(MessageType.PLAYER_FLEET_LAND, cls._instance.handle_land)  # 新增
        return cls._instance

    def handle_arrival(self, message: Message):  # 修改
        """处理舰队到达事件"""
        player = self.game.player_manager.get_player_by_id(message.data["player_id"])
        if not player:
            return

        # 检查是否靠近星球
        for world in self.game.world_manager.world_instances.values():
            distance = self.game.rule_manager.calculate_distance(message.data["location"], (world.x, world.y, world.z))
            if distance <= player.fleet.travel_speed:  # 如果靠近星球
                # 触发探索事件 (示例)
                if world.object_id not in player.explored_planets:
                    player.explored_planets.append(world.object_id)
                    self.game.log.info(f"玩家 {message.data['player_id']} 探索了星球 {world.world_config.world_id}！")
                    # 在这里添加触发其他事件的逻辑 (例如，与星球上的其他势力交战)
                    # 可以根据 world 的属性来决定触发什么事件

                    # 添加探索奖励 (如果有)
                    for reward in world.exploration_rewards:
                        self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                            "target_id": message.data["player_id"],
                            "target_type": "Player",
                            "resource_id": reward[0],
                            "modifier": "INCREASE",
                            "quantity": reward[1],
                            "duration": 0,  # 立即生效
                        }, self)
                # 标记玩家舰队已经降落, 移动到handle_land里
                # player.fleet.landed_on = world.object_id
                return  # 如果已经触发了星球相关的事件，则不再处理其他事件

        # 如果没有靠近任何星球，则触发与坐标相关的事件 (例如，发现太空废墟、遭遇虫洞等)
        self.game.log.info(f"玩家 {message.data['player_id']} 的舰队到达了坐标 {message.data['location']}！")
        # 示例：发现太空废墟，获得一些资源
        # self.game.message_bus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, { ... }, self)

    def handle_land(self, message: Message):  # 新增
        """处理舰队降落事件"""
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

        # 在这里添加降落后的事件 (例如，与星球上的势力互动、开始采集资源等)
    
    def tick(self, tick_counter):
        if tick_counter % self.tick_interval == 0:
            # interaction_manager的tick逻辑
            pass