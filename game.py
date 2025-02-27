# game.py
from loader.locale import Locale
from loader.enums import *
from message_bus import MessageBus, MessageType
from robot import Robot
import random  # Import random here


class Game:
    def __init__(self):
        self.building_manager = None
        self.event_manager = None
        self.modifier_manager = None
        self.world_manager = None
        self.player_manager = None
        self.current_round: int = 0

        self.robot = None

    def add_robot(self, resource_configs, building_configs):
        # 创建玩家
        player = self.player_manager.create_player(resource_configs, building_configs)  # 使用 create_player 方法
        player.fleet.location = self.world_manager.pick()
        self.robot = Robot(player, self)

    def handle_player_action(self, player, action_data: dict):
        """处理玩家行动 (现在通过消息)"""
        action = action_data['action']

        if action == 'move':
            target_planet_id = action_data['target_planet_id']
            # 发送移动舰队的消息
            MessageBus.post_message(MessageType.PLAYER_MOVE_FLEET, {
                "player_id": player.player_id,
                "world_id": target_planet_id,
            }, player)
            print(f"玩家 {player.player_id} 请求移动到星球 {target_planet_id}")

        elif action == 'build':
            planet_id = action_data['planet_id']
            building_id = action_data['building_id']
            # 发送建造建筑的消息
            MessageBus.post_message(MessageType.BUILDING_REQUEST, {
                "player_id": player.player_id,
                "world_id": planet_id,
                "building_id": building_id,
            }, player)
            print(f"玩家 {player.player_id} 请求在星球 {planet_id} 建造建筑 {building_id}")

        elif action == 'upgrade':
            building_id = action_data['building_id']
            # 发送升级建筑的消息
            MessageBus.post_message(MessageType.BUILDING_UPGRADE_REQUEST, {
                "player_id": player.player_id,
                "building_id": building_id,
            }, player)
            print(f"玩家 {player.player_id} 请求升级建筑 {building_id}")


    def run(self):
        """游戏主循环"""
        while True:
            self.current_round += 1
            print(f"当前回合: {self.current_round}")

            # 生成和处理事件
            self.event_manager.tick()

            # 玩家思考并执行操作 (现在由 Robot 通过消息完成)
            action_data = self.robot.think()  # 获取完整的行动决策
            action_text = Locale.get_text(f"action_{action_data['action']}") # 获取行动名称
            print(f"玩家操作: {action_text}")

            self.handle_player_action(self.robot.player, action_data)

            # 更新建筑状态和处理资源产出
            self.building_manager.tick()

            # 更新 modifier
            self.modifier_manager.tick()

            # 处理消息
            MessageBus.tick()

            # 检查建筑和事件延迟完成情况 (现在通过消息处理)

            # 等待用户输入
            user_input = input("按回车键继续，输入 'r' 查看资源，输入 'p' 查看已探索星球及建筑：").strip().lower()
            if user_input == 'r':
                print("当前资源：")
                for resource_id, amount in self.robot.player.resources.items():
                    resource_name = Locale.get_text(resource_id)
                    print(f"{resource_name}: {amount}")
            elif user_input == 'p':
                print("已探索的星球及建筑：")
                for planet in self.robot.player.explored_planets:
                    planet_name = Locale.get_text(planet.world_config.world_id)
                    print(f"星球: {planet_name}")
                    for building_instance in self.building_manager.get_buildings_on_world(planet.object_id):
                        building_name = Locale.get_text(building_instance.building_config.name_id)
                        print(f"  - 建筑: {building_name}")