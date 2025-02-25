import random
from loader.enums import *

def handle_event(player, event, Locale):
    event_name = Locale.get_text(event.event_name_id)
    print(f"触发事件：{event_name}")
    initial_phase = event.phases[event.initial_phase]
    phase_text = Locale.get_text(initial_phase.text_id)
    print(f"事件初始阶段：{phase_text}")

    options = event.options.get(event.initial_phase, {})
    if options:
        print("可选择的操作：")
        for i, (option_id, option) in enumerate(options.items(), start=1):
            option_text = Locale.get_text(option_id)
            print(f"{i}. {option_text}")

        while True:
            try:
                choice = int(input("请选择操作编号：").strip())
                if 1 <= choice <= len(options):
                    selected_option_id = list(options.keys())[choice - 1]
                    selected_option_text = Locale.get_text(selected_option_id)
                    selected_option = options[selected_option_id]
                    print(f"你选择的操作是：{selected_option_text}")
                    break
                else:
                    print("无效的选择，请重新输入。")
            except ValueError:
                print("输入无效，请输入一个数字。")

        judgment_object = selected_option.judgment_object
        judgment_value = selected_option.value
        if judgment_object != 'None':
            current_value = player.resources.get(judgment_object, 0)
            below = selected_option.below
            equal = selected_option.equal
            greater = selected_option.greater
            if (below and current_value < judgment_value) or \
                    (equal and current_value == judgment_value) or \
                    (greater and current_value > judgment_value):
                print("判定成功！")
                resource_to_change = random.choice(list(player.resources.keys()))
                change_amount = random.randint(-10, 10)
                return {
                    "Total Resources": {
                        resource_to_change: (Modifier.ADD if change_amount > 0 else Modifier.USE, abs(change_amount))
                    }
                }
            else:
                print("判定失败！")
    else:
        print("该阶段没有可选择的操作。")
    return {}