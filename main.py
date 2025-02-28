# main.py
from loader.world_configs import load_world_configs
from loader.resource import load_resources_from_csv
from loader.building_config import load_buildings_from_csv
from loader.event_config import load_events_from_csv
from loader.locale import Locale
from managers.building_manager import BuildingManager
from managers.event_manager import EventManager
from managers.modifier_manager import ModifierManager
from managers.world_manager import WorldManager
from managers.player_manager import PlayerManager
from managers.rule_manager import RulesManager
from managers.interaction_manager import InteractionManager
from game import Game
from logger import Log
import logging

def main():
    Locale.load_from_csv('resources/locale.csv')
    Locale.set_language("cn")

    resource_configs = load_resources_from_csv('resources/resources.csv')
    building_configs = load_buildings_from_csv('resources/buildings.csv')
    event_configs = load_events_from_csv(
        event_info='resources/event_info.csv',
        event_phases='resources/event_phases.csv',
        event_options='resources/event_options.csv',
        event_results='resources/event_results.csv'
    )
    world_configs = load_world_configs(
        world_info_file='resources/world_info.csv',
        world_init_structures_file='resources/world_init_structures.csv',
        world_explored_rewards_file='resources/world_explored_rewards.csv'
    )

    game = Game()

    world_manager = WorldManager(world_configs, game)
    event_manager = EventManager(event_configs, game)
    building_manager = BuildingManager(building_configs, game)
    player_manager = PlayerManager(game)
    modifier_manager = ModifierManager(game)
    rule_manager = RulesManager(game)
    interaction_manager = InteractionManager(game)  # 新增：初始化 InteractionManager

    game.building_manager = building_manager
    game.event_manager = event_manager
    game.modifier_manager = modifier_manager
    game.world_manager = world_manager
    game.player_manager = player_manager
    game.rule_manager = rule_manager
    game.interaction_manager = interaction_manager  # 新增：将 InteractionManager 添加到 Game 对象

    worlds = world_manager.generate_worlds(100)

    game.add_robot(resource_configs, building_configs)

    # 初始化Log，可以设置日志级别和文件名
    log = Log(level=logging.DEBUG)

    game.run()

if __name__ == "__main__":
    main()