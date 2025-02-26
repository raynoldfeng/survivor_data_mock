import csv


def read_csv(file_path):
    data = []
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(row)
    return data


def check_event_branches(event_info_path, event_phases_path, event_options_path, event_results_path):
    event_info = read_csv(event_info_path)
    event_phases = read_csv(event_phases_path)
    event_options = read_csv(event_options_path)
    event_results = read_csv(event_results_path)

    # 存储每个事件的所有阶段
    event_phase_dict = {}
    for phase in event_phases:
        event_id = phase['event_id']
        if event_id not in event_phase_dict:
            event_phase_dict[event_id] = []
        event_phase_dict[event_id].append(phase['phase_id'])

    # 存储每个阶段的所有选项
    phase_option_dict = {}
    for option in event_options:
        phase_id = option['phase_id']
        if phase_id not in phase_option_dict:
            phase_option_dict[phase_id] = []
        phase_option_dict[phase_id].append(option['option_id'])

    # 存储每个选项对应的结果
    option_result_dict = {}
    for result in event_results:
        # 假设 event_options 表中已添加 result_id 字段来关联结果
        for option in event_options:
            if option.get('result_id') == result['result_id']:
                option_id = option['option_id']
                if option_id not in option_result_dict:
                    option_result_dict[option_id] = []
                option_result_dict[option_id].append(result['result_id'])

    # 遍历 event_info 中的每个事件
    for info in event_info:
        event_id = info['event_id']
        initial_phase = info['initial_phase']

        # 检查初始阶段是否存在
        if event_id not in event_phase_dict or initial_phase not in event_phase_dict[event_id]:
            print(f"Event {event_id}: 初始阶段 {initial_phase} 缺失")
            continue

        # 开始遍历阶段
        current_phase = initial_phase
        while current_phase:
            # 检查该阶段是否有选项
            if current_phase not in phase_option_dict:
                print(f"Event {event_id}, Phase {current_phase}: 没有选项，请确认是否无选择阶段")
            else:
                # 遍历该阶段的所有选项
                for option_id in phase_option_dict[current_phase]:
                    # 检查选项是否有对应的结果
                    if option_id not in option_result_dict:
                        print(f"Event {event_id}, Phase {current_phase}, Option {option_id}: 缺少结果")

            # 找到下一个阶段
            current_phase_info = next((p for p in event_phases if p['event_id'] == event_id and p['phase_id'] == current_phase), None)
            next_success_phase = current_phase_info.get('next_phase_success')
            next_failure_phase = current_phase_info.get('next_phase_failure')

            if next_success_phase:
                if next_success_phase not in event_phase_dict[event_id]:
                    print(f"Event {event_id}, Phase {current_phase}: 成功后的下一阶段 {next_success_phase} 缺失")
                current_phase = next_success_phase
            elif next_failure_phase:
                if next_failure_phase not in event_phase_dict[event_id]:
                    print(f"Event {event_id}, Phase {current_phase}: 失败后的下一阶段 {next_failure_phase} 缺失")
                current_phase = next_failure_phase
            else:
                current_phase = None


# 请根据实际情况修改文件路径
event_info_path = 'resources/event_info.csv'
event_phases_path = 'resources/event_phases.csv'
event_options_path = 'resources/event_options.csv'  # 使用修复后的 event_options 文件
event_results_path = 'resources/event_results.csv'

check_event_branches(event_info_path, event_phases_path, event_options_path, event_results_path)