from loader.locale import Locale
import random

def handle_player_action(player, event_manager, building_manager, worlds, action, slow_move_remaining_rounds, print_resource_change):
    if slow_move_remaining_rounds > 0:
        slow_move_remaining_rounds -= 1
        if slow_move_remaining_rounds == 0:
            target_planet_index = random.randint(0, len(worlds) - 1)
            target_planet = worlds[target_planet_index]
            player.move_to_planet(target_planet)
            # 打印探索获得资源信息
            rewards = target_planet.exploration_rewards
            if rewards:
                planet_name = Locale.get_text(target_planet.world_config.world_id)
                print(f"探索星球 {planet_name} 获得资源：")
                for resource_id, quantity in rewards:
                    old_amount = player.resources.get(resource_id, 0)
                    player.resources[resource_id] = old_amount + quantity
                    new_amount = player.resources[resource_id]
                    print_resource_change(resource_id, old_amount, new_amount)
            planet_name = Locale.get_text(target_planet.world_config.world_id)
            print(f"缓慢移动完成，Player 移动到了星球 {planet_name}（索引：{target_planet_index}）")
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
                    planet_name = Locale.get_text(target_planet.world_config.world_id)
                    print(f"探索星球 {planet_name} 获得资源：")
                    for resource_id, quantity in rewards:
                        old_amount = player.resources.get(resource_id, 0)
                        player.resources[resource_id] = old_amount + quantity
                        new_amount = player.resources[resource_id]
                        print_resource_change(resource_id, old_amount, new_amount)
                planet_name = Locale.get_text(target_planet.world_config.world_id)
                print(f"消耗 1.0 promethium，Player 移动到了星球 {planet_name}（索引：{target_planet_index}）")
            else:
                slow_move_remaining_rounds = 3
                planet_name = Locale.get_text(target_planet.world_config.world_id)
                print(f"promethium 资源不足，开始缓慢移动，将在 3 个回合后到达星球 {planet_name}（索引：{target_planet_index}）")
        elif action == 'build':
            planet = player.fleet["planet"]
            building_to_build = player.select_building_to_build(planet)
            if building_to_build:
                if building_manager.build_building(player, planet, building_to_build):
                    # 打印建筑成功信息
                    planet_name = Locale.get_text(planet.world_config.world_id)
                    building_name = Locale.get_text(building_to_build.name_id)
                    print(f"在星球 {planet_name} 成功建造建筑 {building_name}")
                else:
                    planet_name = Locale.get_text(planet.world_config.world_id)
                    building_name = Locale.get_text(building_to_build.name_id)
                    print(f"无法在星球 {planet_name} 上建造 {building_name}。")
        elif action == 'upgrade':
            planet = player.fleet["planet"]
            building_to_upgrade = player.select_building_to_upgrade(planet)
            if building_to_upgrade:
                if building_manager.upgrade_building(player, planet, building_to_upgrade):
                    # 打印升级成功信息
                    planet_name = Locale.get_text(planet.world_config.world_id)
                    old_building_name = Locale.get_text(building_to_upgrade.name_id)
                    next_level_building = building_manager.get_next_level_building(building_to_upgrade)
                    new_building_name = Locale.get_text(next_level_building.name_id)
                    print(f"在星球 {planet_name} 成功将建筑 {old_building_name} 升级为 {new_building_name}")
                else:
                    planet_name = Locale.get_text(planet.world_config.world_id)
                    building_name = Locale.get_text(building_to_upgrade.name_id)
                    print(f"无法在星球 {planet_name} 上升级建筑 {building_name}。")
    return slow_move_remaining_rounds