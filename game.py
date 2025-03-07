from loader.locale import Locale
from loader.enums import *
from managers.robot import Robot
from path_finder import Pathfinder
from logger import Log
import logging
from time import sleep

class Game:
    def __init__(self):
        self.building_manager = None
        self.event_manager = None
        self.modifier_manager = None
        self.world_manager = None
        self.player_manager = None
        self.rule_manager = None
        self.message_bus = None
        self.robot = None
        self.tick_counter = 0
        self.log = Log(level=logging.DEBUG, filename="log.txt")
        self.pathfinder = Pathfinder(self) 

    def add_robot(self, resources, building_configs):
        player = self.player_manager.create_player(resources, building_configs)
        self.robot = self.player_manager.add_robot(player)


    def run(self):
        while True:
            self.tick_counter += 1  # 增加总tick计数
            self.log.info(f"当前tick: {self.tick_counter}")
            self.event_manager.tick(self.tick_counter) 
            self.player_manager.tick(self.tick_counter) 
            self.building_manager.tick(self.tick_counter) 
            self.modifier_manager.tick(self.tick_counter) 
            self.rule_manager.tick(self.tick_counter)
            self.message_bus.tick(self.tick_counter)

            # 以下是为了管理员查看方便
            '''    
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
            '''
            sleep(1)