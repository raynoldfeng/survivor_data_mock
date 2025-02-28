# robot.py
from loader.locale import Locale
from loader.enums import Target
from message_bus import MessageBus, MessageType
import random

class Robot(): 
    def __init__(self, player_id, game):
        self.player_id = player_id  # 关联的 Player ID
        self.game = game

    def can_build_on_slot(self, planet, building_config):
        """判断是否可以在指定星球的插槽上建造指定建筑"""
        player = self.game.player_manager.get_player_by_id(self.player_id)

        # 1. 检查资源是否足够
        for resource_id, modifier_dict in building_config.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == "USE":
                    if player.resources.get(resource_id, 0) < quantity:
                        return False

        # 2. 检查是否已经有同类型建筑 (根据 building_config.type 判断)
        # 并且，如果是资源型建筑，还需要检查是否和已有的建筑 subtype 重复
        for building_instance in self.game.building_manager.get_buildings_on_world(planet.object_id):
            if building_instance.building_config.type == building_config.type:
                if building_config.type == "RESOURCE":
                    # 如果是资源型建筑，检查 subtype 是否相同
                    if building_instance.building_config.subtype == building_config.subtype:
                        return False  # 不允许相同 subtype 的资源建筑
                else:
                    return False  # 非资源型建筑，不允许同类型

        # 3. 检查星球类型限制
        if building_config.type == "RESOURCE":
            allowed_planet_types = planet.world_config.resource_slots.get(building_config.subtype.value, [])
            if not allowed_planet_types:
                return False
        # 此处不需要检查非Resource类型的建筑，因为在 select_building_to_build 中已经根据 available_buildings 进行了过滤。

        # 4. 检查前置建筑
        if building_config.type == "GENERAL":
            required_building_type = building_config.subtype.value
            if required_building_type != "NONE":
                has_required_building = False
                for building_instance in self.game.building_manager.get_buildings_on_world(planet.object_id):
                      if building_instance.building_config.type == "GENERAL" and building_instance.building_config.subtype.value == required_building_type:
                        has_required_building = True
                        break
                if not has_required_building:
                    return False

        return True

    def can_upgrade_building(self, building_instance):
        """判断是否可以升级指定建筑"""
        player = self.game.player_manager.get_player_by_id(self.player_id)
        # 检查是否有下一级建筑
        if not building_instance.building_config.next_level_id:
            return False

        next_level_building_config = self.game.building_manager.get_building_config(building_instance.building_config.next_level_id)
        if not next_level_building_config:
            return False

        # 检查资源是否足够
        for resource_id, modifier_dict in next_level_building_config.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == 'USE':
                    if player.resources.get(resource_id, 0) < quantity:
                        return False
        return True

    def select_building_to_build(self, planet):
        """选择要在指定星球上建造的建筑 (改进版)"""
        player = self.game.player_manager.get_player_by_id(self.player_id)
        available_buildings = []

        for building_id, building_config in player.avaliable_building_config.items():
            if self.can_build_on_slot(planet, building_config):
                available_buildings.append(building_config)
        if not available_buildings:
            return None

        # 1. 优先选择能增加关键资源的建筑 (例如，钷素和能量)
        key_resource_buildings = [
            b for b in available_buildings
            if any("promethium" in modifier_dict or "energy" in modifier_dict for modifier_dict in b.modifiers.values())
        ]
        if key_resource_buildings:
            return random.choice(key_resource_buildings)

        # 2. 其次，选择能增加其他资源的建筑
        resource_buildings = [
            b for b in available_buildings
            if any("PRODUCTION" in modifier_dict for modifier_dict in b.modifiers.values())
        ]
        if resource_buildings:
            return random.choice(resource_buildings)
        # 3. 否则，选择能增加人口的建筑
        population_buildings = [
            b for b in available_buildings
            if any("population" in modifier_dict for modifier_dict in b.modifiers.values())
        ]

        if population_buildings:
            return random.choice(population_buildings)

        # 4. 最后，随机选择一个可建造的建筑
        return random.choice(available_buildings)

    def select_building_to_upgrade(self):
        """选择要升级的建筑 (改进版)"""
        player = self.game.player_manager.get_player_by_id(self.player_id)
        upgradeable_buildings = []

        for planet_id in list(player.planets_buildings.keys()):
            building_ids = player.planets_buildings.get(planet_id)
            if not building_ids:
                continue
            for building_id in building_ids:
                building_instance = self.game.building_manager.get_building_instance(building_id)
                if not building_instance:
                    continue
                if self.can_upgrade_building(building_instance):
                    upgradeable_buildings.append(building_instance)

        if not upgradeable_buildings:
            return None

        # 1. 优先升级能增加关键资源的建筑
        key_resource_buildings = [
            b for b in upgradeable_buildings
            if any("promethium" in modifier_dict or "energy" in modifier_dict
                   for modifier_dict in self.game.building_manager.get_building_config(b.building_config.next_level_id).modifiers.values())
        ]
        if key_resource_buildings:
            return random.choice(key_resource_buildings)

        # 2. 其次，升级能增加其他资源的建筑
        resource_buildings = [
            b for b in upgradeable_buildings
            if any("PRODUCTION" in modifier_dict
                   for modifier_dict in self.game.building_manager.get_building_config(b.building_config.next_level_id).modifiers.values())
        ]
        if resource_buildings:
            return random.choice(resource_buildings)
        # 3. 否则，升级能增加人口的建筑
        population_buildings =  [
            b for b in upgradeable_buildings
            if any("population" in modifier_dict
                   for modifier_dict in self.game.building_manager.get_building_config(b.building_config.next_level_id).modifiers.values())
        ]
        if population_buildings:
            return random.choice(population_buildings)

        # 4. 最后，随机选择一个可升级的建筑
        return random.choice(upgradeable_buildings)

    def evaluate_planet(self, planet):
        """评估星球的价值"""
        # 资源价值
        resource_value = 0
        for resource_id, slots in planet.resource_slots.items():
            resource_value += slots * 0.5  # 假设每个资源槽位价值 0.5

        # 战略位置 (简化：距离出生点越近，价值越高)
        player = self.game.player_manager.get_player_by_id(self.player_id)
        if isinstance(player.fleet.location, str):
             distance = self.game.world_manager.calculate_distance(player.fleet.location, planet.object_id)
        else:
            distance = self.game.world_manager.calculate_distance(player.fleet.location, (planet.x, planet.y, planet.z))

        strategic_value = 10 / (distance + 1)  # 避免除以零

        # 总价值
        total_value = resource_value + strategic_value
        return total_value

    def select_planet_to_explore(self):
        """选择要探索的星球"""
        player = self.game.player_manager.get_player_by_id(self.player_id)
        # 获取未探索的星球
        unexplored_planets = [
            self.game.world_manager.get_world_by_id(planet_id)
            for planet_id in self.game.world_manager.world_instances.keys()
            if planet_id not in player.explored_planets and planet_id != player.fleet.location
        ]

        if not unexplored_planets:
            return None

        # 根据距离和潜在价值进行评估
        best_planet = None
        best_score = -1

        for planet in unexplored_planets:
            if not planet:
                continue
            if isinstance(player.fleet.location, str):
                distance = self.game.world_manager.calculate_distance(player.fleet.location, planet.object_id)
            else:
                distance = self.game.world_manager.calculate_distance(player.fleet.location, (planet.x, planet.y, planet.z))
            potential_value = self.evaluate_planet(planet)  # 评估星球价值
            score = potential_value / (distance + 1)  # 距离越近，价值越高

            if score > best_score:
                best_score = score
                best_planet = planet

        return best_planet

    def handle_event(self):
        """处理当前发生的事件 (简化版)"""
        player = self.game.player_manager.get_player_by_id(self.player_id)
        # 获取当前玩家的事件
        event = self.game.event_manager.active_events[Target.PLAYER].get(player.player_id)
        if not event:
            return None

        current_phase = event.current_phase
        if not current_phase:
            return None

        # 如果需要选择选项，则随机选择一个
        if current_phase.options and current_phase.phase_id not in event.choices:
            choice = random.choice(list(current_phase.options.keys()))
            return {
                "action": "select_event_option",
                "player_id": player.player_id,
                "choice": choice,
            }

        return None

    def think(self):
        """模拟玩家思考并返回行动"""
        player = self.game.player_manager.get_player_by_id(self.player_id)

        # 0. 处理事件
        event_action = self.handle_event()
        if event_action:
            return event_action

        # 1. 尝试升级
        building_instance = self.select_building_to_upgrade()
        if building_instance:
            return {
                "action": "upgrade",
                "building_id": building_instance.object_id,
                "player_id": player.player_id
            }

        # 2. 尝试建造
        explored_planets = [self.game.world_manager.get_world_by_id(pid) for pid in player.explored_planets]
        available_planets = [p for p in explored_planets if p]
        if available_planets:
            available_planets.sort(key=self.evaluate_planet, reverse=True)
            for planet in available_planets:
                if not planet:
                    continue
                building_config = self.select_building_to_build(planet)
                if building_config:
                    return {
                        "action": "build",
                        "planet_id": planet.object_id,
                        "building_id": building_config.building_id,
                        "player_id": player.player_id
                    }

        # 3. 尝试探索/移动
        planet_to_explore = self.select_planet_to_explore()  # 获取最值得探索的星球

        if planet_to_explore:
            # 如果已经在移动中，则有一定概率中断当前移动 (模拟玩家改变主意)
            if player.fleet.destination:
                if random.random() < 0.3:  # 30% 的概率中断移动
                    travel_method = "subspace_jump" if player.resources.get("promethium", 0) > 50 else "slow_travel"
                    return {
                        "action": "move",
                        "target_planet_id": planet_to_explore.object_id,
                        "travel_method": travel_method,
                        "player_id": player.player_id
                    }

            # 如果没有在移动中，或者没有选择中断移动，则选择移动方式
            travel_method = "subspace_jump" if player.resources.get("promethium", 0) > 50 else "slow_travel"
            return {
                "action": "move",
                "target_planet_id": planet_to_explore.object_id,
                "travel_method": travel_method,
                "player_id": player.player_id
            }

        return {"action": "none", "player_id": player.player_id}

    def tick(self, game):
        """Robot 的 tick 方法，调用 think 并返回操作数据"""
        return self.think()