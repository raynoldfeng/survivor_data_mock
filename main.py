from loader.world import load_world_configs, create_world
from loader.resource import load_resources_from_csv
from loader.building import load_buildings_from_csv
from loader.events import load_events_from_csv
from loader.locale import Locale
import random
from player import Player
from event_logic import handle_event
from building_logic import (
    get_next_level_building,
    build_cost_check,
    build_cost_apply,
    upgrade_cost_check,
    upgrade_cost_apply
)
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


# 生成 100 个世界
worlds = world_generator(100, world_configs)

# 创建 Player 对象
player = Player(resources, worlds, buildings)

# 记录缓慢移动的剩余回合数
slow_move_remaining_rounds = 0

while True:
    print("请选择操作：")
    print("e: 触发事件")
    print("q: 退出")
    print("r: 查看当前的资源总和")
    print("n: 进行一个回合的动作（移动、建造等）")
    choice = input().strip().lower()

    if choice == 'e':
        event = random.choice(event_list)
        event_result = handle_event(player, event, Locale)
        for target, modifier_dict in event_result.items():
            for resource_id, (modifier, quantity) in modifier_dict.items():
                if target == "Total Resources":
                    if modifier == Modifier.ADD:
                        player.resources[resource_id] = player.resources.get(resource_id, 0) + quantity
                    elif modifier == Modifier.USE:
                        player.resources[resource_id] = max(0, player.resources.get(resource_id, 0) - quantity)
    elif choice == 'q':
        break
    elif choice == 'r':
        print("当前资源总和：")
        for resource, amount in player.resources.items():
            print(f"{resource}: {amount}")
    elif choice == 'n':
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
                        print(f"{resource_id}: {quantity}")
                print(f"缓慢移动完成，Player 移动到了星球 {target_planet.world_config.world_id}（索引：{target_planet_index}）")
            else:
                print(f"正在缓慢移动，还需 {slow_move_remaining_rounds} 个回合到达目标星球。")
            continue

        action = player.think()
        if action == 'move':
            target_planet_index = random.randint(0, len(worlds) - 1)
            target_planet = worlds[target_planet_index]
            promethium_amount = player.resources.get('resource.promethium', 0)
            if promethium_amount >= 1.0:
                player.resources['resource.promethium'] -= 1.0
                player.move_to_planet(target_planet)
                # 打印探索获得资源信息
                rewards = target_planet.exploration_rewards
                if rewards:
                    print(f"探索星球 {target_planet.world_config.world_id} 获得资源：")
                    for resource_id, quantity in rewards:
                        print(f"{resource_id}: {quantity}")
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
                    build_cost_apply(player, building_to_build)
                    player.planet_buildings[planet.world_config.world_id].append(building_to_build)
                    print(f"在星球 {planet.world_config.world_id} 成功建造了建筑 {building_to_build.name_id}")
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
                            build_cost_apply(player, building_to_build)
                            player.planet_buildings[target_planet.world_config.world_id].append(building_to_build)
                            print(f"在星球 {target_planet.world_config.world_id} 成功建造了建筑 {building_to_build.name_id}")
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
                            upgrade_cost_apply(player, next_level_building)
                            index = player.planet_buildings[target_planet.world_config.world_id].index(building_to_upgrade)
                            player.planet_buildings[target_planet.world_config.world_id][index] = next_level_building
                            print(f"在星球 {target_planet.world_config.world_id} 成功将建筑 {building_to_upgrade.name_id} 升级为 {next_level_building.name_id}")
                        else:
                            print(f"资源不足，无法在星球 {target_planet.world_config.world_id} 上升级建筑 {building_to_upgrade.name_id}。")
                    else:
                        print(f"星球 {target_planet.world_config.world_id} 没有可升级的建筑。")
            else:
                print("还没有探索过的星球，无法下达命令。")
    else:
        print("无效的选择，请重新输入。")
