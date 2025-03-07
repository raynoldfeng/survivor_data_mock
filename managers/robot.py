from loader.locale import Locale
from loader.enums import Target, BuildingType
import random

class Robot():
    def __init__(self, player_id, game):
        self.player_id = player_id
        self.game = game

    def can_build_on_slot(self, planet, building_config):
        """判断是否可以在指定星球的插槽上建造指定建筑, 需要考虑建筑类型和星球槽位类型的匹配"""
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
                if building_config.type == BuildingType.RESOURCE:
                    # 如果是资源型建筑，检查 subtype 是否相同
                    if building_instance.building_config.subtype == building_config.subtype:
                        return False  # 不允许相同 subtype 的资源建筑
                else:
                    return False  # 非资源型建筑，不允许同类型

        # 3. 检查前置建筑
        if building_config.type == BuildingType.GENERAL:
            required_building_type = building_config.subtype.value
            if required_building_type != "NONE":
                has_required_building = False
                for building_instance in self.game.building_manager.get_buildings_on_world(planet.object_id):
                      if building_instance.building_config.type == BuildingType.GENERAL and building_instance.building_config.subtype.value == required_building_type:
                        has_required_building = True
                        break
                if not has_required_building:
                    return False

        # 4. 检查是否有空闲的对应类型槽位 (根据 building_config.type 判断)
        if building_config.type == BuildingType.RESOURCE:
            slot_type = "resource"
        elif building_config.type == BuildingType.GENERAL:
            slot_type = "general"
        elif building_config.type == BuildingType.DEFENSE:
            slot_type = "defense"
        else:
            return False  # 未知建筑类型，无法建造

        # 直接调用 world 的 get_available_slot 方法
        if planet.get_available_slot(slot_type) is None:
            return False  # 没有空闲的槽位

        return True

    def can_upgrade_building(self, building_instance):
        """判断是否可以升级指定建筑"""
        player = self.game.player_manager.get_player_by_id(self.player_id)
        # 检查是否有下一级建筑
        if not building_instance.building_config.get_next_level_id():
            return False

        next_level_building_config = self.game.building_manager.get_building_config(building_instance.building_config.get_next_level_id())
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
                   for modifier_dict in self.game.building_manager.get_building_config(b.building_config.get_next_level_id()).modifiers.values())
        ]
        if key_resource_buildings:
            return random.choice(key_resource_buildings)

        # 2. 其次，升级能增加其他资源的建筑
        resource_buildings = [
            b for b in upgradeable_buildings
            if any("PRODUCTION" in modifier_dict
                   for modifier_dict in self.game.building_manager.get_building_config(b.building_config.get_next_level_id()).modifiers.values())
        ]
        if resource_buildings:
            return random.choice(resource_buildings)
        # 3. 否则，升级能增加人口的建筑
        population_buildings =  [
            b for b in upgradeable_buildings
            if any("population" in modifier_dict
                   for modifier_dict in self.game.building_manager.get_building_config(b.building_config.get_next_level_id()).modifiers.values())
        ]
        if population_buildings:
            return random.choice(population_buildings)

        # 4. 最后，随机选择一个可升级的建筑
        return random.choice(upgradeable_buildings)

    def evaluate_planet(self, planet):
        """评估星球的价值"""
        # 资源价值
        resource_value = 0
        for slot_type, slots in planet.building_slots.items():
            # 根据槽位类型给予不同的权重 (可以根据您的游戏设计调整)
            if slot_type == "resource":
                resource_value += len(slots) * 0.8  # 资源槽位权重较高
            elif slot_type == "general":
                resource_value += len(slots) * 0.5  # 通用槽位权重中等
            elif slot_type == "defense":
                resource_value += len(slots) * 0.3  # 防御槽位权重较低

        # 战略位置 (简化：距离出生点越近，价值越高)
        player = self.game.player_manager.get_player_by_id(self.player_id)
        distance = self.game.world_manager.calculate_distance(player.fleet.location, planet.location) #直接使用location
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
            if planet_id not in player.explored_planets and planet_id != player.fleet.landed_on # 修改这里，使用landed_on
        ]

        if not unexplored_planets:
            return None

        # 根据距离和潜在价值进行评估
        best_planet = None
        best_score = -1

        for planet in unexplored_planets:
            if not planet:
                continue
            else:
                distance = self.game.world_manager.calculate_distance(player.fleet.location, planet.location) #直接使用location

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
        self.game.log.info(f"Robot {player.player_id} 开始思考...")

        # 0. 检查舰队是否正在移动
        if player.fleet.path:
            self.game.log.info(f"Robot {player.player_id} 的舰队正在移动中，跳过本轮思考。")
            return {"action": "none", "player_id": player.player_id}

        # 1. 检查是否已到达星球接触面且未降落, 如果是, 则降落
        if player.fleet.final_destination and not player.fleet.landed_on:
            world = self.game.world_manager.get_world_at_location(player.fleet.final_destination)
            if world:
                self.game.log.info(f"Robot {player.player_id} 尝试降落在星球 {world.world_config.world_id} 上。")
                return {
                    "action": "land",
                    "player_id": player.player_id,
                    "world_id": world.object_id,  # 降落需要星球 ID
                }

        # 2. 检查是否已降落且未探索 (这部分逻辑可能不需要在 Robot 中，而是在 EventManager 中处理)
        if player.fleet.landed_on:
            world = self.game.world_manager.get_world_by_id(player.fleet.landed_on)
            if world and world.object_id not in player.explored_planets:
                self.game.log.info(f"Robot {player.player_id} 准备探索星球 {world.world_config.world_id}。")


        # 3. 处理事件
        event_action = self.handle_event()
        if event_action:
            self.game.log.info(f"Robot {player.player_id} 选择处理事件: {event_action}")
            return event_action

        # 4. 尝试升级
        building_instance = self.select_building_to_upgrade()
        if building_instance:
            self.game.log.info(f"Robot {player.player_id} 选择升级建筑: {building_instance.building_config.name_id}")
            return {
                "action": "upgrade",
                "building_id": building_instance.object_id,
                "player_id": player.player_id
            }

        # 5. 尝试建造
        explored_planets = [self.game.world_manager.get_world_by_id(pid) for pid in player.explored_planets]
        available_planets = [p for p in explored_planets if p]
        if available_planets:
            available_planets.sort(key=self.evaluate_planet, reverse=True)
            self.game.log.info(f"Robot {player.player_id} 正在评估可建造星球...")
            for planet in available_planets:
                if not planet:
                    continue
                building_config = self.select_building_to_build(planet)
                if building_config:
                    self.game.log.info(f"Robot {player.player_id} 选择在类型为{planet.world_config.world_id}的星球 {planet.object_id} 上建造建筑 {building_config.building_id}")
                    return {
                        "action": "build",
                        "planet_id": planet.object_id,
                        "building_id": building_config.building_id,
                        "player_id": player.player_id
                    }

        # 6. 尝试探索/移动
        planet_to_explore = self.select_planet_to_explore()  # 获取最值得探索的星球

        if planet_to_explore:
            self.game.log.info(f"Robot {player.player_id} 考虑前往类型为{planet_to_explore.world_config.world_id}的星球 {planet_to_explore.object_id},坐标({planet_to_explore.location}...")
            if player.get_resource_amount("promethium") >= self.game.rule_manager.SUBSPACE_JUMP_COST:
                travel_method = "subspace_jump"
            else:
                travel_method = "slow_travel"  # 没有足够的资源跃迁，则尝试slow_travel
            
            if travel_method == "subspace_jump":
                self.game.log.info(f"Robot {player.player_id} 选择 {travel_method} 前往类型为{planet_to_explore.world_config.world_id}的星球 {planet_to_explore.object_id}。")
                return {
                    "action": "move",
                    "target_planet_id": planet_to_explore.object_id,
                    "travel_method": travel_method,
                    "player_id": player.player_id
                }
            elif travel_method == "slow_travel":
                # 尝试寻路
               if travel_method == "slow_travel":
                # 尝试寻路
                start_location = player.fleet.location
                end_location = planet_to_explore.location #直接使用location
                path = self.game.pathfinder.find_path(start_location, end_location, target_type="world") #移除grid
                if path:
                    # 找到路径，设置路径和最终目标
                    player.fleet.set_path(path)
                    player.fleet.set_final_destination(planet_to_explore.object_id) #设置id, 而不是坐标
                    self.game.log.info(f"Robot {player.player_id} 选择 {travel_method} 前往类型为{planet_to_explore.world_config.world_id}的星球 {planet_to_explore.object_id}，并找到了路径。")
                    return {
                        "action": "move",
                        "target_planet_id": planet_to_explore.object_id,
                        "travel_method": travel_method,
                        "player_id": player.player_id
                    }
                else:
                    self.game.log.warn(f"Robot {player.player_id} 无法找到前往星球 {planet_to_explore.object_id} 的路径。")
                    return {"action": "none", "player_id": player.player_id}

        self.game.log.info(f"Robot {player.player_id} 没有找到合适的行动。")
        return {"action": "none", "player_id": player.player_id}

    def tick(self, game):
        """Robot 的 tick 方法，调用 think 并返回操作数据"""
        return self.think()