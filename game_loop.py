from loader.enums import *
from loader.locale import Locale
from action_handler import handle_player_action
import random


def print_resource_change(resource_id, old_amount, new_amount):
    change = new_amount - old_amount
    resource_name = Locale.get_text(resource_id)
    if change > 0:
        print(f"资源 {resource_name} 增加了 {change}，当前数量: {new_amount}")
    elif change < 0:
        print(f"资源 {resource_name} 减少了 {abs(change)}，当前数量: {new_amount}")


def game_loop(player, event_manager, building_manager, worlds, slow_move_remaining_rounds, modifier_manager):

    round_number = 0
    while True:
        round_number += 1
        print(f"当前回合: {round_number}")

        # 为玩家生成新事件
        new_events = event_manager.generate_events(player)
        for event_instance in new_events:
            event_name = Locale.get_text(event_instance.name_id)
            print(f"触发事件: {event_name}")

        # 事件主循环
        need_user_choice = event_manager.tick(player)
        for event_instance in need_user_choice:
            current_phase = event_instance.phases.get(event_instance.current_phase_id)
            if current_phase:
                phase_text = Locale.get_text(current_phase.text_id)
                print(f"事件阶段: {phase_text}")

                phase_options = event_instance.options.get(current_phase.phase_id, {})
                print("所有选项信息：")
                for option_id, option in phase_options.items():
                    option_text = Locale.get_text(option.option_id)
                    print(f"{option_id}. {option_text}")

                    # 打印选项判定条件
                    judgment_conditions = []
                    if option.below:
                        judgment_conditions.append(f"{option.judgment_object} < {option.value}")
                    if option.equal:
                        judgment_conditions.append(f"{option.judgment_object} == {option.value}")
                    if option.greater:
                        judgment_conditions.append(f"{option.judgment_object} > {option.value}")
                    if judgment_conditions:
                        print(f"  选项判定条件：{' 或 '.join(judgment_conditions)}")
                    else:
                        print("  选项判定条件：无")

                    # 打印奖励资源
                    result_list = event_instance.results.get(option.result_id, [])
                    if result_list:
                        print("  奖励资源：")
                        for result in result_list:
                            resource_name = Locale.get_text(result.resource_type_id)
                            target_text = ""
                            if event_instance.target == Target.PLANET:
                                target = random.choice(worlds)
                                target_text = f"星球 {Locale.get_text(target.world_config.world_id)} 的"
                            elif event_instance.target == Target.BUILDING:
                                all_buildings = []
                                for player_buildings in building_manager.player_buildings.values():
                                    all_buildings.extend(player_buildings)
                                if all_buildings:
                                    target = random.choice(all_buildings)
                                    target_text = f"建筑 {Locale.get_text(target.name_id)} 的"
                                else:
                                    print("没有可用的建筑，跳过此效果。")
                                    continue
                            elif event_instance.target == Target.FLEET:
                                target = player.fleet.resources
                                target_text = "舰队的"
                            elif event_instance.target == Target.RESOURCES:
                                target = player.resources
                                target_text = "玩家资源的"
                            elif event_instance.target == Target.CHARACTER:
                                target = player.character.resources
                                target_text = "角色的"

                            if result.modifier == Modifier.INCREASE:
                                print(f"    {target_text}{resource_name} 一次性增加 {result.quantity}")
                            elif result.modifier == Modifier.REDUCE:
                                print(f"    {target_text}{resource_name} 一次性扣除 {result.quantity}")
                            elif result.modifier == Modifier.PRODUCTION:
                                print(f"    {target_text}{resource_name} 单位时间产出增加 {result.quantity}")
                            elif result.modifier == Modifier.COST:
                                print(f"    {target_text}{resource_name} 单位时间消耗增加 {result.quantity}")

                            modifier_manager.add_modifier(target, result.modifier, result.resource_type_id, result.quantity, int(result.duration))
                    else:
                        print("  奖励资源：无")

                while True:
                    try:
                        choice = input("请选择一个选项 (输入选项 ID): ")
                        if choice in phase_options:
                            break
                        else:
                            print("无效的选择，请重新输入。")
                    except ValueError:
                        print("输入无效，请输入有效的选项 ID。")

                event_manager.handle_user_choice(player, event_instance, choice)

        # 玩家思考并执行操作
        action = player.think()
        action_text = Locale.get_text(f"action_{action}")
        print(f"玩家操作: {action_text}")

        slow_move_remaining_rounds = handle_player_action(player, event_manager, building_manager, worlds, action, slow_move_remaining_rounds, print_resource_change)

        # 更新建筑状态和处理资源产出
        building_manager.tick()

        modifier_manager.tick()

        # 检查建筑和事件延迟完成情况
        completed_buildings = player.check_building_completion(building_manager)
        for building in completed_buildings:
            building_name = Locale.get_text(building.building_config.name_id)
            print(f"建筑 {building_name} 建造完成")
        completed_upgrades = player.check_upgrade_completion(building_manager)
        for upgrade in completed_upgrades:
            old_building_name = Locale.get_text(upgrade.old_building.name_id)
            new_building_name = Locale.get_text(upgrade.new_building.name_id)
            print(f"建筑 {old_building_name} 升级为 {new_building_name} 完成")

        # 等待用户输入
        user_input = input("按回车键继续，输入 'r' 查看资源，输入 'p' 查看已探索星球及建筑：").strip().lower()
        if user_input == 'r':
            print("当前资源总和：")
            for resource, amount in player.resources.items():
                resource_name = Locale.get_text(resource)
                print(f"{resource_name}: {amount}")
        elif user_input == 'p':
            print("已探索的星球及建筑：")
            for planet in player.explored_planets:
                planet_name = Locale.get_text(planet.world_config.world_id)
                print(f"星球 ID: {planet_name}")
                for building in player.planet_buildings.get(planet.world_config.world_id, []):
                    building_name = Locale.get_text(building.name_id)
                    print(f"  - 建筑: {building_name}")