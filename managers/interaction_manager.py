# managers/interaction_manager.py
from typing import Dict
from message_bus import MessageBus, MessageType
from game import Game

class InteractionManager:
    _instance = None

    def __new__(cls, game: Game):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.game = game
            cls._instance.game.interaction_manager = cls._instance  # 将自身添加到 Game 对象中
        return cls._instance

    def tick(self):
        for message in MessageBus.get_messages(type=MessageType.FLEET_ARRIVE):
            self.handle_arrival(message)

    def handle_arrival(self, message: "Message"):
        """处理舰队到达事件"""
        player_id = message.data["player_id"]
        location = message.data["location"]  # 现在 location 始终是坐标
        player = self.game.player_manager.get_player_by_id(player_id)

        # 检查是否靠近星球
        for world in self.game.world_manager.world_instances.values():
            distance = self.game.rule_manager.calculate_distance(location, (world.x, world.y, world.z))
            if distance <= player.fleet.travel_speed:  # 如果靠近星球
                # 触发探索事件 (示例)
                if world.object_id not in player.explored_planets:
                    player.explored_planets.append(world.object_id)
                    self.game.log.info(f"玩家 {player_id} 探索了星球 {world.world_config.world_id}！")

                    # 在这里添加触发其他事件的逻辑 (例如，与星球上的其他势力交战)
                    # 可以根据 world 的属性来决定触发什么事件

                    # 添加探索奖励 (如果有)
                    for reward in world.exploration_rewards:
                         MessageBus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, {
                            "target_id": player_id,
                            "target_type": "Player",
                            "resource_id": reward[0],
                            "modifier": "INCREASE",
                            "quantity": reward[1],
                            "duration": 0,  # 立即生效
                        }, self)
                return  # 如果已经触发了星球相关的事件，则不再处理其他事件

        # 如果没有靠近任何星球，则触发与坐标相关的事件 (例如，发现太空废墟、遭遇虫洞等)
        self.game.log.info(f"玩家 {player_id} 的舰队到达了坐标 {location}！")
        # 示例：发现太空废墟，获得一些资源
        # MessageBus.post_message(MessageType.MODIFIER_PLAYER_RESOURCE, { ... }, self) # 资源获取统一改成MODIFIER_PLAYER_RESOURCE