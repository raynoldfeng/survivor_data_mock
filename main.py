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
from game import Game
import random

def main():
    # 加载多语言数据
    Locale.load_from_csv('resources/locale.csv')
    Locale.set_language("cn")

    # 加载资源数据
    resource_configs = load_resources_from_csv('resources/resources.csv')
    # 加载建筑数据
    building_configs = load_buildings_from_csv('resources/buildings.csv')

    # 加载事件数据
    event_configs = load_events_from_csv(
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

    # 创建 Game 对象
    game = Game()

    # 初始化管理器
    world_manager = WorldManager(world_configs, game)
    event_manager = EventManager(event_configs, game)
    building_manager = BuildingManager(building_configs, game)
    player_manager = PlayerManager(game)
    modifier_manager = ModifierManager(game)

    # 生成星球
    worlds = world_manager.generate_worlds(100)

    game.add_robot(resource_configs, building_configs)
    # 启动游戏循环
    game.run()

if __name__ == "__main__":
    main()