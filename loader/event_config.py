from common import *
from basic_types.enums import *

class EventPhase:
    def __init__(self, phase_id, previous_phase, next_phase_success, next_phase_failure, text_id, duration):
        self.phase_id = phase_id
        self.previous_phase = previous_phase
        self.next_phase_success = next_phase_success
        self.next_phase_failure = next_phase_failure
        self.text_id = text_id
        self.duration = duration
        self.options = {}  # 存储option_id到EventOption的映射

class EventOption:
    def __init__(self, option_id, success_result_id, fail_result_id):
        self.option_id = option_id
        self.success_result_id = success_result_id
        self.fail_result_id = fail_result_id
        self.challenges = []  # 存储多个EventChallenge实例

class EventChallenge:
    def __init__(self, challenge_id, resource_type, value, below, equal, greater):
        self.challenge_id = challenge_id
        self.resource_type = resource_type
        self.value = float(value)
        self.below = below.lower() == 'true'
        self.equal = equal.lower() == 'true'
        self.greater = greater.lower() == 'true'

class EventResult:
    def __init__(self, result_id, resource_type_id, modifier, quantity, duration):
        self.result_id = result_id
        self.resource_type_id = resource_type_id
        self.modifier = modifier
        self.quantity = float(quantity)
        self.duration = duration

class EventConfig:
    def __init__(self, event_id, event_name_id, trigger_probability, trigger_text_id, initial_phase, target):
        self.event_id = event_id
        self.event_name_id = event_name_id
        self.trigger_probability = trigger_probability
        self.trigger_text_id = trigger_text_id
        self.initial_phase = initial_phase
        self.target = target
        self.phases = {}  # 存储phase_id到EventPhase的映射
        self.results = {}  # 存储result_id到EventResult的映射

    def add_phase(self, phase):
        self.phases[phase.phase_id] = phase

    def add_option(self, phase_id, option):
        if phase_id in self.phases:
            self.phases[phase_id].options[option.option_id] = option

    def add_result(self, result):
        if result.result_id not in self.results:
            self.results[result.result_id] = []
        self.results[result.result_id].append(result)

def load_events_from_csv(**kwargs):
    event_info_file = kwargs.get('event_info')
    event_phases_file = kwargs.get('event_phases')
    event_options_file = kwargs.get('event_options')
    event_challenges_file = kwargs.get('event_challenges')
    event_results_file = kwargs.get('event_results')
    events = {}

    # 加载事件基本信息
    if event_info_file:
        with open(event_info_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                event_id = row['event_id']
                event = EventConfig(
                    event_id,
                    row['event_name_id'],
                    float(row['trigger_probability']),
                    row['trigger_text_id'],
                    row['initial_phase'],
                    ObjectType(row['target'])
                )
                events[event_id] = event

    # 加载事件阶段信息
    if event_phases_file:
        with open(event_phases_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                event_id = row['event_id']
                phase = EventPhase(
                    row['phase_id'],
                    row['previous_phase'],
                    row['next_phase_success'],
                    row['next_phase_failure'],
                    row['text_id'],
                    int(row['duration'])
                )
                if event_id in events:
                    events[event_id].add_phase(phase)

    # 加载选项信息
    if event_options_file:
        with open(event_options_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                phase_id = row['phase_id']
                option = EventOption(
                    row['option_id'],
                    row['success_result_id'],
                    row['fail_result_id']
                )
                for event in events.values():
                    if phase_id in event.phases:
                        event.add_option(phase_id, option)
    # 加载挑战条件 (修正部分)
    if event_challenges_file:
        with open(event_challenges_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                option_id = row['option_id']
                challenge = EventChallenge(
                    row['challenge_id'],
                    row['resource_type'],
                    row['value'],
                    row['below'],
                    row['equal'],
                    row['greater']
                )
                # 找到对应的 EventOption 并添加挑战
                for event in events.values():
                    for phase in event.phases.values():
                        if option_id in phase.options:
                            phase.options[option_id].challenges.append(challenge)


    # 加载结果信息
    if event_results_file:
        with open(event_results_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                result_id = row['result_id']
                resource_type_id = row['resource_type_id']
                modifier = ModifierType(row["modifier"])
                quantity = row['quantity']
                duration = row['duration']
                result = EventResult(result_id, resource_type_id, modifier, quantity, duration)
                for event in events.values():
                    event.add_result(result)

    return list(events.values())