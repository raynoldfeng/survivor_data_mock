# main.py
from loader.world import load_world_configs
from loader.resource import load_resources_from_csv
from loader.building_config import load_buildings_from_csv
from loader.event_config import load_events_from_csv
from loader.locale import Locale
from building_manager import BuildingManager
from event_manager import EventManager
from modifier_manager import ModifierManager
from world_manager import WorldManager
from player import Player
from game_loop import game_loop
import random


def main():
    # 加载多语言数据
    Locale.load_from_csv('resources/locale.csv')
    Locale.set_language("cn")

    # 加载资源数据
    resources = load_resources_from_csv('resources/resources.csv')
    # 加载建筑数据
    building_config = load_buildings_from_csv('resources/buildings.csv')

    # 加载事件数据
    event_config = load_events_from_csv(
        event_info='resources/event_info.csv',
        event_phases='resources/event_phases.csv',
        event_options='resources/event_options.csv',
        event_results='resources/event_results.csv'
    )

    # 加载世界配置
    world_configs = load_world_configs(
        world_info_file='resources/world_info.csv',
        world_init_structures_file='resources/world_init_structures.csv',
        world_explored_rewards_file='resources/world_explored_rewards.csv'
    )

    # 创建 Player 对象
    player = Player(resources)

    # 创建世界管理器
    world_manager = WorldManager(world_configs)
    # 初始化事件管理器
    event_manager = EventManager(event_config)

    # 初始化建筑管理器
    building_manager = BuildingManager(building_config)

    # 记录缓慢移动的剩余回合数
    slow_move_remaining_rounds = 0

    # 初始化 ModifierManager
    modifier_manager = ModifierManager()

    worlds = world_manager.generate_worlds(100)
    player.set_avaliable_buildings(building_config)
    player.move_to_planet(random.choice(worlds))
    game_loop(player, event_manager, building_manager, worlds, slow_move_remaining_rounds, modifier_manager)

if __name__ == "__main__":
    main()