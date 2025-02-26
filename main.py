from loader.world import load_world_configs, create_world
from loader.resource import load_resources_from_csv
from loader.building import load_buildings_from_csv
from loader.events import load_events_from_csv
from loader.locale import Locale
from building_logic import (
    get_next_level_building,
    build_cost_check,
    build_cost_apply,
    upgrade_cost_check,
    upgrade_cost_apply
)
import random
from player import Player
from event_logic import handle_event
from loader.enums import Modifier


# 加载多语言数据
Locale.load_from_csv('resources/locale.csv')
Locale.set_language("cn")

# 加载资源数据
resources = load_resources_from_csv('resources/resources.csv')
# 加载建筑数据
buildings = load_buildings_from_csv('resources/buildings.csv')

event_list = load_events_from_csv(
    event_info='resources/event_info.csv',
    event_phases='resources/event_phases.csv',
    event_options='resources/event_options.csv',
)

# 加载世界配置
world_configs = load_world_configs(
    world_info_file='resources/world_info.csv',
    world_init_structures_file='resources/world_init_structures.csv',
    world_explored_rewards_file='resources/world_explored_rewards.csv'
)


# 世界生成器函数
def world_generator(num_worlds, world_configs):
    worlds = []
    world_ids = list(world_configs.keys())
    probabilities = [world_configs[world_id].info['occur'] for world_id in world_ids]

    for _ in range(num_worlds):
        selected_world_id = random.choices(world_ids, weights=probabilities)[0]
        world_config = world_configs[selected_world_id]
        world = create_world(world_config)
        worlds.append(world)

    return worlds


def print_resource_change(resource_id, old_amount, new_amount):
    change = new_amount - old_amount
    if change > 0:
        print(f"资源 {resource_id} 增加了 {change}，当前数量: {new_amount}")
    elif change < 0:
        print(f"资源 {resource_id} 减少了 {abs(change)}，当前数量: {new_amount}")


def main():
    # 生成 100 个世界
    worlds = world_generator(100, world_configs)

    # 创建 Player 对象
    player = Player(resources, worlds, buildings)

    # 记录缓慢移动的剩余回合数
    slow_move_remaining_rounds = 0

    round_number = 0
    while True:
        round_number += 1
        print("-----------------------------------")
        print(f"当前回合: {round_number}")

        # 每回合自动触发事件
        for event in event_list:
            if random.random() < event.trigger_probability:
                event_result = handle_event(player, event, Locale)
                print(f"完成了事件: {event.event_name_id}")
                for target, modifier_dict in event_result.items():
                    for resource_id, (modifier, quantity) in modifier_dict.items():
                        if target == "Total Resources":
                            old_amount = player.resources.get(resource_id, 0)
                            if modifier == Modifier.ADD:
                                player.resources[resource_id] = old_amount + quantity
                            elif modifier == Modifier.USE:
                                player.resources[resource_id] = max(0, old_amount - quantity)
                            new_amount = player.resources[resource_id]
                            print_resource_change(resource_id, old_amount, new_amount)

        # 玩家思考并执行操作
        action = player.think()
        print(f"玩家操作: {action}")

        if slow_move_remaining_rounds > 0:
            slow_move_remaining_rounds -= 1
            if slow_move_remaining_rounds == 0:
                target_planet_index = random.randint(0, len(worlds) - 1)
                target_planet = worlds[target_planet_index]
                player.move_to_planet(target_planet)
                # 打印探索获得资源信息
                rewards = target_planet.exploration_rewards
                if rewards:
                    print(f"探索星球 {target_planet.world_config.world_id} 获得资源：")
                    for resource_id, quantity in rewards:
                        old_amount = player.resources.get(resource_id, 0)
                        player.resources[resource_id] = old_amount + quantity
                        new_amount = player.resources[resource_id]
                        print_resource_change(resource_id, old_amount, new_amount)
                print(f"缓慢移动完成，Player 移动到了星球 {target_planet.world_config.world_id}（索引：{target_planet_index}）")
            else:
                print(f"正在缓慢移动，还需 {slow_move_remaining_rounds} 个回合到达目标星球。")
        else:
            if action == 'move':
                target_planet_index = random.randint(0, len(worlds) - 1)
                target_planet = worlds[target_planet_index]
                promethium_amount = player.resources.get('resource.promethium', 0)
                if promethium_amount >= 1.0:
                    old_amount = promethium_amount
                    player.resources['resource.promethium'] = old_amount - 1.0
                    new_amount = player.resources['resource.promethium']
                    print_resource_change('resource.promethium', old_amount, new_amount)
                    player.move_to_planet(target_planet)
                    # 打印探索获得资源信息
                    rewards = target_planet.exploration_rewards
                    if rewards:
                        print(f"探索星球 {target_planet.world_config.world_id} 获得资源：")
                        for resource_id, quantity in rewards:
                            old_amount = player.resources.get(resource_id, 0)
                            player.resources[resource_id] = old_amount + quantity
                            new_amount = player.resources[resource_id]
                            print_resource_change(resource_id, old_amount, new_amount)
                    print(f"消耗 1.0 promethium，Player 移动到了星球 {target_planet.world_config.world_id}（索引：{target_planet_index}）")
                else:
                    slow_move_remaining_rounds = 3
                    print(f"promethium 资源不足，开始缓慢移动，将在 3 个回合后到达星球 {target_planet.world_config.world_id}（索引：{target_planet_index}）")
            elif action == 'build':
                planet = player.fleet["planet"]
                building_to_build = player.select_building_to_build(planet)
                if building_to_build:
                    if build_cost_check(player, building_to_build):
                        # 打印准备建筑信息
                        print(f"准备在星球 {planet.world_config.world_id} 建造建筑 {building_to_build.name_id}")
                        old_resources = player.resources.copy()
                        build_cost_apply(player, building_to_build)
                        for resource_id, old_amount in old_resources.items():
                            new_amount = player.resources[resource_id]
                            print_resource_change(resource_id, old_amount, new_amount)
                        # 使用回合数管理建筑
                        building_instance = player.start_building(building_to_build, planet)
                        if building_instance:
                            print(f"开始建造建筑 {building_to_build.name_id}，剩余回合数: {building_instance.remaining_rounds}")
                    else:
                        print(f"资源不足，无法在星球 {planet.world_config.world_id} 上建造 {building_to_build.name_id}。")
                else:
                    print(f"星球 {planet.world_config.world_id} 没有可用的空格建造 1 级建筑。")
            elif action == 'command':
                target_planet = player.select_target_planet()
                if target_planet:
                    command = player.select_command()
                    if command == "build":
                        building_to_build = player.select_building_to_build(target_planet)
                        if building_to_build:
                            if build_cost_check(player, building_to_build):
                                # 打印准备建筑信息
                                print(f"准备在星球 {target_planet.world_config.world_id} 建造建筑 {building_to_build.name_id}")
                                old_resources = player.resources.copy()
                                build_cost_apply(player, building_to_build)
                                for resource_id, old_amount in old_resources.items():
                                    new_amount = player.resources[resource_id]
                                    print_resource_change(resource_id, old_amount, new_amount)
                                # 使用回合数管理建筑
                                building_instance = player.start_building(building_to_build, target_planet)
                                if building_instance:
                                    print(f"开始建造建筑 {building_to_build.name_id}，剩余回合数: {building_instance.remaining_rounds}")
                            else:
                                print(f"资源不足，无法在星球 {target_planet.world_config.world_id} 上建造 {building_to_build.name_id}。")
                        else:
                            print(f"星球 {target_planet.world_config.world_id} 没有可用的空格建造 1 级建筑。")
                    elif command == "upgrade":
                        building_to_upgrade = player.select_building_to_upgrade(target_planet)
                        if building_to_upgrade:
                            next_level_building = get_next_level_building(building_to_upgrade, player.buildings)
                            if upgrade_cost_check(player, next_level_building):
                                # 打印准备升级建筑信息
                                print(f"准备在星球 {target_planet.world_config.world_id} 将建筑 {building_to_upgrade.name_id} 升级为 {next_level_building.name_id}")
                                old_resources = player.resources.copy()
                                upgrade_cost_apply(player, next_level_building)
                                for resource_id, old_amount in old_resources.items():
                                    new_amount = player.resources[resource_id]
                                    print_resource_change(resource_id, old_amount, new_amount)
                                # 使用回合数管理升级
                                upgrade_instance = player.start_upgrade(building_to_upgrade, next_level_building, target_planet)
                                if upgrade_instance:
                                    print(f"开始升级建筑 {building_to_upgrade.name_id} 为 {next_level_building.name_id}，剩余回合数: {upgrade_instance.remaining_rounds}")
                            else:
                                print(f"资源不足，无法在星球 {target_planet.world_config.world_id} 上升级建筑 {building_to_upgrade.name_id}。")
                        else:
                            print(f"星球 {target_planet.world_id} 没有可升级的建筑。")
                else:
                    print("还没有探索过的星球，无法下达命令。")

        # 检查建筑和事件延迟完成情况
        completed_buildings = player.check_building_completion()
        for building in completed_buildings:
            print(f"建筑 {building.building_config.name_id} 建造完成")
        completed_upgrades = player.check_upgrade_completion()
        for upgrade in completed_upgrades:
            print(f"建筑 {upgrade.old_building.name_id} 升级为 {upgrade.new_building.name_id} 完成")

        # 等待用户输入
        user_input = input("按回车键继续，输入 'r' 查看资源，输入 'p' 查看已探索星球及建筑：").strip().lower()
        if user_input == 'r':
            print("当前资源总和：")
            for resource, amount in player.resources.items():
                print(f"{resource}: {amount}")
        elif user_input == 'p':
            print("已探索的星球及建筑：")
            for planet in player.explored_planets:
                print(f"星球 ID: {planet.world_config.world_id}")
                for building in player.planet_buildings.get(planet.world_config.world_id, []):
                    print(f"  - 建筑: {building.name_id}")


if __name__ == "__main__":
    main()
