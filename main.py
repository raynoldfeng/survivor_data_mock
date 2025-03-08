from loader.world_configs import load_world_configs
from loader.resource import load_resources_from_csv
from loader.building_config import load_building_configs
from loader.event_config import load_events_from_csv
from loader.locale import Locale
from managers.building_manager import BuildingManager
from managers.event_manager import EventManager
from managers.modifier_manager import ModifierManager
from managers.world_manager import WorldManager
from managers.player_manager import PlayerManager
from managers.rule_manager import RulesManager
from managers.message_bus import MessageBus
from game import Game

def main():
    Locale.load_from_csv('resources/locale.csv')
    Locale.set_language("cn")

    resource_configs = load_resources_from_csv('resources/resources.csv')

    building_configs = load_building_configs(
        buildings_file='resources/buildings.csv', 
        building_modifiers_file='resources/building_modifiers.csv'
        )
    
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

    # message_bus优先初始化
    message_bus = MessageBus(game)
    game.message_bus = message_bus

    world_manager = WorldManager(world_configs, game)
    event_manager = EventManager(event_configs, game)
    building_manager = BuildingManager(building_configs, game)
    player_manager = PlayerManager(game)
    modifier_manager = ModifierManager(game)
    rule_manager = RulesManager(game)

    game.building_manager = building_manager
    game.event_manager = event_manager
    game.modifier_manager = modifier_manager
    game.world_manager = world_manager
    game.player_manager = player_manager
    game.rule_manager = rule_manager

    game.generate_worlds(1)

    game.add_robot(resource_configs, building_configs)

    game.run()

main()