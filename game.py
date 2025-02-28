# game.py
from loader.locale import Locale
from loader.enums import *
from message_bus import MessageBus, MessageType
from managers.robot import Robot
from logger import Log

class Game:
    def __init__(self):
        self.building_manager = None
        self.event_manager = None
        self.modifier_manager = None
        self.world_manager = None
        self.player_manager = None
        self.rule_manager = None
        self.interaction_manager = None
        self.current_round: int = 0
        self.robot = None
        self.log = Log()

    def add_robot(self, resources, building_configs):
        player = self.player_manager.create_player(resources, building_configs)
        self.robot = self.player_manager.add_robot(player)


    def run(self):
        while True:
            self.current_round += 1
            self.log.info(f"当前回合: {self.current_round}")
            self.event_manager.tick()

            # PlayerManager.tick() 会处理所有 Player (包括 Robot) 的操作
            self.player_manager.tick()

            self.building_manager.tick()
            self.modifier_manager.tick()
            self.rule_manager.tick()
            self.interaction_manager.tick()  # 新增：调用 InteractionManager 的 tick
            MessageBus.tick()

            # 以下是为了管理员查看方便
            user_input = input("按回车键继续，输入 'r' 查看资源，输入 'p' 查看已探索星球及建筑：").strip().lower()
            if user_input == 'r':
                self.log.info("当前资源：")
                for resource_id, amount in self.robot.resources.items():
                    self.log.info(f"{resource_id}: {amount}")
            elif user_input == 'p':
                self.log.info("已探索的星球及建筑：")
                for planet_id in self.robot.explored_planets:
                    planet = self.world_manager.get_world_by_id(planet_id)
                    planet_name = Locale.get_text(planet.world_config.world_id)
                    self.log.info(f"星球: {planet_name} ({planet.x}, {planet.y}, {planet.z})")
                    for building_instance in self.building_manager.get_buildings_on_world(planet_id):
                        building_name = Locale.get_text(building_instance.building_config.name_id)
                        self.log.info(f"  - 建筑: {building_name}")