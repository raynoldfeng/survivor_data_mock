from loader.enums import *
import random
from .message_bus import MessageType, Message  # 导入 MessageType

class Robot():
    def __init__(self, player_id, game):
        self.player_id = player_id
        self.game = game
        self.dest_world = None

    def can_build_on_slot(self, planet, building_config):
        """判断是否可以在指定星球的插槽上建造指定建筑, 需要考虑建筑类型和星球槽位类型的匹配"""
        player = self.game.player_manager.get_player_by_id(self.player_id)

        # 1. 检查资源是否足够 (在 BuildingManager 中检查)

        # 2. 检查建筑等级 (只有 1 级建筑才能直接建造)
        if building_config.level != 1:
            return False
        
        # 4. 检查前置建筑
        if not self.game.building_manager._has_prerequisite_building(building_config, planet.object_id):
            return False

        # 5. 检查是否有空闲的对应类型槽位 (根据 building_config.type 判断)
        if building_config.type == BuildingType.RESOURCE:
            slot_type = "resource"
            subtype = building_config.subtype.value  # 获取 subtype
        elif building_config.type == BuildingType.GENERAL:
            slot_type = "general"
            subtype = None
        elif building_config.type == BuildingType.DEFENSE:
            slot_type = "defense"
            subtype = None
        else:
            return False  # 未知建筑类型，无法建造

        # 调用 BuildingManager 的 get_available_slot 方法
        if self.game.building_manager.get_available_slot(planet.object_id, slot_type, subtype) is None:
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

        # 检查资源是否足够 (在 BuildingManager 中检查)
        return True

    def select_building_to_build(self, planet):
        """选择要在指定星球上建造的建筑"""
        player = self.game.player_manager.get_player_by_id(self.player_id)
        available_buildings = []

        for building_id, building_config in player.avaliable_building_config.items():
            if self.can_build_on_slot(planet, building_config):
                available_buildings.append(building_config)

        if not available_buildings:
            return None

        # 优先选择 1 级建筑
        level_1_buildings = [b for b in available_buildings if b.level == 1]
        if level_1_buildings:
            # 在 1 级建筑中，按照之前的逻辑选择（关键资源 > 其他资源 > 人口 > 随机）
            key_resource_buildings = [
                b for b in level_1_buildings
                if any(
                    modifier_data['resource_id'] in ("resource.promethium", "resource.energy")  # 假设有 energy 资源
                    for modifier_data in b.modifiers  # 直接从 building_config.modifiers 获取
                    if modifier_data['modifier_type'] == Modifier.PRODUCTION
                )
            ]
            if key_resource_buildings:
                return random.choice(key_resource_buildings)

            resource_buildings = [
                b for b in level_1_buildings
                if any(
                    modifier_data['modifier_type'] == Modifier.PRODUCTION
                    for modifier_data in b.modifiers  # 直接从 building_config.modifiers 获取
                )
            ]
            if resource_buildings:
                return random.choice(resource_buildings)

            population_buildings = [
                b for b in level_1_buildings
                if any(
                    modifier_data['resource_id'] == "resource.population"
                    for modifier_data in b.modifiers  # 直接从 building_config.modifiers 获取
                    if modifier_data['modifier_type'] == Modifier.PRODUCTION
                )
            ]
            if population_buildings:
                return random.choice(population_buildings)

            return random.choice(level_1_buildings)
        else:
            # 如果没有 1 级建筑，则不建造 (理论上不应该出现这种情况)
            return None
        
    def calculate_building_upgrade_benefit(self, building_instance):
        """计算建筑升级的收益 (简化版，仅考虑资源产出)"""
        next_level_config = self.game.building_manager.get_building_config(building_instance.building_config.get_next_level_id())
        if not next_level_config:
            return 0

        current_production = 0
        next_level_production = 0

        # 获取当前等级的产出
        # current_modifiers = self.game.building_manager.building_modifiers.get(building_instance.building_config.building_id, []) # 不需要了
        for modifier_data in building_instance.building_config.modifiers: # 直接从 building_config.modifiers 获取
            if modifier_data['modifier_type'] == Modifier.PRODUCTION:
                current_production += modifier_data['quantity']

        # 获取下一等级的产出
        # next_level_modifiers = self.game.building_manager.building_modifiers.get(next_level_config.building_id, []) # 不需要了
        for modifier_data in next_level_config.modifiers: # 直接从 next_level_config.modifiers 获取
            if modifier_data['modifier_type'] == Modifier.PRODUCTION:
                next_level_production += modifier_data['quantity']

        return next_level_production - current_production

    def select_building_to_upgrade(self):
        """选择要升级的建筑 (改进版)"""
        player = self.game.player_manager.get_player_by_id(self.player_id)
        upgradeable_buildings = []

        for planet_id in list(player.planets_buildings.keys()):
            building_ids = player.planets_buildings.get(planet_id)
            if not building_ids:
                continue
            for building_id in building_ids:
                building_instance = self.game.building_manager.get_building_by_id(building_id)
                if not building_instance:
                    continue
                if self.can_upgrade_building(building_instance):
                    upgradeable_buildings.append(building_instance)

        if not upgradeable_buildings:
            return None

        # 根据收益选择要升级的建筑
        best_building = None
        best_benefit = -1

        for building_instance in upgradeable_buildings:
            benefit = self.calculate_building_upgrade_benefit(building_instance)
            if benefit > best_benefit:
                best_benefit = benefit
                best_building = building_instance

        return best_building # 如果没有值得升级的建筑，则返回 None

    def evaluate_planet(self, planet):
        """评估星球的价值"""
        # 资源价值
        resource_value = 0
        for slot_type, slots in planet.building_slots.items():
            # 根据槽位类型给予不同的权重 (可以根据您的游戏设计调整)
            if slot_type == "resource":
                # resource 类型需要累加二级字典中的所有值
                for subtype, num_slots in slots.items():
                    resource_value += num_slots * 0.8  # 资源槽位权重较高
            elif slot_type == "general":
                for subtype, num_slots in slots.items():
                    resource_value += num_slots * 0.5  # 资源槽位权重较高
            elif slot_type == "defense":
                for subtype, num_slots in slots.items():
                    resource_value += num_slots * 0.3  # 资源槽位权重较高

        # 战略位置 (简化：距离出生点越近，价值越高)
        player = self.game.player_manager.get_player_by_id(self.player_id)
        distance = self.game.world_manager.calculate_distance(player.fleet.location, planet.location)
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
        if player.fleet.path and player.fleet.path.lengh()>0:
            self.game.log.info(f"Robot {player.player_id} 的舰队正在移动中，跳过本轮思考。")
            return {"action": "none", "player_id": player.player_id}

        # 1. 检查是否已到达星球接触面且未降落, 如果是, 则降落
        if self.dest_world is not None and player.fleet.landed_on is None:
            world = self.game.world_manager.get_world_by_id(self.dest_world)
            if world:
                # 检查舰队是否在星球表面
                if world.is_on_surface(player.fleet.location):
                    self.dest_world = None
                    self.game.log.info(f"Robot {player.player_id} 尝试降落在星球 {world.world_config.world_id} 上。")
                    return {
                        "action": "land",  # 改为 "land"
                        "player_id": player.player_id,
                        "world_id": world.object_id,
                    }

        # 2. 检查是否已降落且未探索
        if player.fleet.landed_on is not None:
            #  检查是否需要起飞
            world = self.game.world_manager.get_world_by_id(player.fleet.landed_on)
            if world and world.object_id not in player.explored_planets:
                self.game.log.info(f"Robot {player.player_id} 准备探索星球 {world.world_config.world_id}。")
                # 发送探索星球的消息
                return {
                    "action": "explore",
                    "player_id": player.player_id,
                    "world_id": world.object_id,
                }
            else:
                # 已经探索过, 或者不在星球上, 则起飞
                self.game.log.info(f"Robot {player.player_id} 准备起飞。")
                return {
                    "action": "takeoff",  # 新增 "takeoff" 操作
                    "player_id": player.player_id,
                }

        # 3. 处理事件
        event_action = self.handle_event()
        if event_action:
            self.game.log.info(f"Robot {player.player_id} 选择处理事件: ")
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
                self.game.log.info(f"Robot {player.player_id} 选择  前往类型为{planet_to_explore.world_config.world_id}的星球 {planet_to_explore.object_id}。")
                # 获取星球表面的一个可用坐标
                destination_coordinate = self.game.world_manager.get_spawn_location(planet_to_explore)
                if destination_coordinate:
                    player.fleet.set_destination(destination_coordinate)
                    self.dest_world = planet_to_explore.object_id  # 记录目标星球
                    return {
                        "action": "move",
                        "target_planet_id": planet_to_explore.object_id, # 保持ID不变, 但实际dest已经是坐标
                        "travel_method": travel_method,
                        "player_id": player.player_id
                    }
                else:
                    self.game.log.warn(f"Robot {player.player_id} 无法找到星球 {planet_to_explore.object_id} 的可到达位置，跃迁失败。")
                    return {"action": "none", "player_id": player.player_id}

            elif travel_method == "slow_travel":
                # 尝试寻路
                start_location = player.fleet.location
                # 获取星球表面的一个可用坐标
                end_location = self.game.world_manager.get_spawn_location(planet_to_explore)
                if not end_location:
                    self.game.log.warn(f"Robot {player.player_id} 无法找到星球 {planet_to_explore.object_id} 的可到达位置, 无法移动。")
                    return {"action": "none", "player_id": player.player_id}
                
                # 寻路
                path = self.game.pathfinder.find_path(start_location, end_location, target_type="world", target_world_id = planet_to_explore.object_id)

                if path == []:
                    # 情况 1: 已经到达星球表面
                    self.game.log.info(f"Robot {player.player_id} 已经位于星球 {planet_to_explore.object_id} 表面，无需移动，准备降落。")
                    #  dest 设置为当前位置
                    player.fleet.set_destination(start_location)
                    self.dest_world = planet_to_explore.object_id  # 记录目标星球
                    return {"action": "none", "player_id": player.player_id}
                elif path:
                    # 情况 2: 找到路径
                    player.fleet.set_path(path)
                    # 将 dest 设置为路径的最后一个坐标
                    player.fleet.set_destination(path[-1])
                    self.dest_world = planet_to_explore.object_id  # 记录目标星球
                    self.game.log.info(f"Robot {player.player_id} 选择  前往类型为{planet_to_explore.world_config.world_id}的星球 {planet_to_explore.object_id}，并找到了路径。")
                    return {
                        "action": "move",
                        "target_planet_id": planet_to_explore.object_id, # 保持ID不变, 但实际dest已经是坐标
                        "travel_method": travel_method,
                        "player_id": player.player_id
                    }
                else:  # path is None
                    # 情况 3: 无法找到路径
                    self.game.log.warn(f"Robot {player.player_id} 无法找到前往星球 {planet_to_explore.object_id} 的路径。")
                    return {"action": "none", "player_id": player.player_id}

        self.game.log.info(f"Robot {player.player_id} 没有找到合适的行动。")
        return {"action": "none", "player_id": player.player_id}

    def tick(self, game):
        """Robot 的 tick 方法，调用 think 并返回操作数据"""
        return self.think()