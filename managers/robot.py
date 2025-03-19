from basic_types.enums import *
from basic_types.resource import Resource
from common import *

class Dest():
    def __init__(self, type, value):
        self.type = type
        self.value = value

class Robot():
    def __init__(self, player_id, game):
        self.object_id = player_id
        self.last_think = datetime.datetime.now()
        self.game = game
        self.dest : Dest = None
    
    # 这里要做成一个tick内的判断，rule里也要对应修改
    def can_afford_building_cost(self, player, building_config):
        for modifier_config in building_config.modifier_configs:
            if modifier_config.modifier_type == ModifierType.LOSS:
                resource = modifier_config.data_type
                quantity = modifier_config.quantity
                avaliable = player.resources.get(resource.id, 0)
                if avaliable < quantity:
                    return False
        return True

    def can_build_on_slot(self, planet, building_config):
        """判断是否可以在指定星球的插槽上建造指定建筑, 需要考虑建筑类型和星球槽位类型的匹配"""
        player = self.game.player_manager.get_player_by_id(self.object_id)

       # 1. 检查建筑等级 (只有 1 级建筑才能直接建造)
        if building_config.level != 1:
            return False
        
        # 2. 检查资源是否足够 (在 BuildingManager 中检查)
        if not self.can_afford_building_cost(player, building_config):
            return False 
        
        # 3. 检查前置建筑
        if not self.game.building_manager._has_prerequisite_building(building_config, planet.object_id):
            return False

        # 4. 检查是否有空闲的对应类型槽位 (根据 building_config.type 判断)
        if building_config.type == BuildingType.RESOURCE:
            slot_type = building_config.type
            subtype = building_config.subtype  # 获取 subtype
        elif building_config.type == BuildingType.GENERAL:
            slot_type = building_config.type
            subtype = None
        elif building_config.type == BuildingType.DEFENSE:
            slot_type = building_config.type
            subtype = None
        else:
            return False  # 未知建筑类型，无法建造

        # 调用 BuildingManager 的 get_available_slot 方法
        if self.game.building_manager.get_available_slot(planet.object_id, slot_type, subtype) is None:
            return False  # 没有空闲的槽位

        return True

    def can_upgrade_building(self, building_instance):
        """判断是否可以升级指定建筑"""
        player = self.game.player_manager.get_player_by_id(self.object_id)
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
        player = self.game.player_manager.get_player_by_id(self.object_id)
        available_buildings = []

        for config_id, building_config in player.avaliable_building_config.items():
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
                    modifier_config.data_type in (Resource.get_resource_by_id("resource.promethium"), Resource.get_resource_by_id("resource.energy"))
                    for modifier_config in b.modifier_configs
                    if modifier_config.modifier_type == ModifierType.PRODUCTION
                )
            ]
            if key_resource_buildings:
                return random.choice(key_resource_buildings)

            resource_buildings = [
                b for b in level_1_buildings
                if any(
                    modifier.modifier_type == ModifierType.PRODUCTION
                    for modifier in b.modifier_configs
                )
            ]
            if resource_buildings:
                return random.choice(resource_buildings)

            population_buildings = [
                b for b in level_1_buildings
                if any(
                    modifier.data_type == Resource.get_resource_by_id("resource.population")
                    for modifier in b.modifier_configs
                    if modifier.modifier_type == ModifierType.PRODUCTION
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
        next_level_config = self.game.building_manager.get_next_level_config(building_instance.building_config)
        if not next_level_config:
            return 0

        current_production = 0
        next_level_production = 0

        # 获取当前等级的产出
        for modifier in building_instance.building_config.modifier_configs:
            if modifier.modifier_type == ModifierType.PRODUCTION:
                current_production += modifier.quantity

        # 获取下一等级的产出
        for modifier in next_level_config.modifier_configs: 
            if modifier.modifier_type == ModifierType.PRODUCTION:
                next_level_production += modifier.quantity


        return next_level_production - current_production

    def select_building_to_upgrade(self):
        """选择要升级的建筑 (改进版)"""
        player = self.game.player_manager.get_player_by_id(self.object_id)
        upgradeable_buildings = []

        for planet_id in player.explored_planets:
            for building_instance in self.game.building_manager.get_buildings_on_world(planet_id):
                # 获取下一级建筑配置
                next_level_building_config = self.game.building_manager.get_next_level_config(building_instance.building_config)
                if next_level_building_config:
                    # 检查资源是否足够
                    can_afford = self.can_afford_building_cost(player, next_level_building_config)
                    if can_afford:
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
        player = self.game.player_manager.get_player_by_id(self.object_id)
        distance = player.fleet.location.distance(planet.location)
        strategic_value = 10 / (distance + 1)  # 避免除以零

        # 总价值
        total_value = resource_value + strategic_value
        return total_value

    def select_planet_to_explore(self):
        """选择要探索的星球 (返回星球列表，按优先级排序)"""
        player = self.game.player_manager.get_player_by_id(self.object_id)
        # 获取未探索的星球
        unexplored_planets = [
            self.game.world_manager.get_world_by_id(planet_id)
            for planet_id in self.game.world_manager.world_instances.keys()
            if planet_id not in player.explored_planets and planet_id != player.fleet.landed_on
        ]

        if not unexplored_planets:
            return []

        # 根据距离和潜在价值进行评估，并排序
        planet_scores = []
        for planet in unexplored_planets:
            if not planet:
                continue
            distance = player.fleet.location.distance(planet.location)
            potential_value = self.evaluate_planet(planet)  # 评估星球价值
            score = potential_value / (distance + 1)  # 距离越近，价值越高
            planet_scores.append((planet, score))

        # 按分数从高到低排序
        planet_scores.sort(key=lambda x: x[1], reverse=True)
        return [planet for planet, score in planet_scores]

    def handle_event(self):
        """处理当前发生的事件 (简化版)"""
        player = self.game.player_manager.get_player_by_id(self.object_id)
        # 获取当前玩家的事件
        event = self.game.event_manager.active_events[ObjectType.PLAYER].get(player.object_id)
        if not event:
            return None

        current_phase = event.current_phase
        if not current_phase:
            return None

        # 如果需要选择选项，则随机选择一个
        if current_phase.options and current_phase.phase_id not in event.choices:
            choice = random.choice(list(current_phase.options.keys()))
            return {
                "action": PlayerAction.CHOICE,
                "player_id": player.object_id,
                "choice": choice,
            }

        return None

    def think(self):
        """模拟玩家思考并返回行动"""
        now = datetime.datetime.now()
        if (now - self.last_think).seconds <=1 :
            return
        
        self.last_think = now
        actions = []
        player = self.game.player_manager.get_player_by_id(self.object_id)
        self.game.log.info(f"Robot {player.object_id} 开始思考...")

        # 检查舰队移动状态
        if self.dest is not None:
            # 有已经规划的路线
            if len(player.fleet.path)>0:
                # 尚未到达，继续移动
                self.game.log.info(f"Robot {player.object_id} 的舰队正在移动中")
            else:
                # 已经到达了某个既定目标

                # 是之前设置的以星球为目标的移动吗？
                if self.dest.type == "world":
                    # 之前的目标是星球
                    world = self.game.world_manager.get_world_by_id(self.dest.value)
                    assert(world)
                    if world.object_id == self.dest.value:
                        if world.is_on_surface(player.fleet.location):
                            # 是目标星球，并且的确到达了表面
                            # 已经到达
                            if player.fleet.landed_on is not None:
                                # 已经降落了，有探索吗？
                                if world.object_id not in player.explored_planets:
                                    # 不在已经探索过的列表里，准备探索
                                    self.game.log.info(f"Robot {player.object_id} 准备探索星球 {world.world_config.world_id} : {world.object_id}。")
                                    actions.append({
                                        "action": PlayerAction.EXPLORE,
                                        "player_id": player.object_id,
                                        "world_id": world.object_id,
                                    })
                                else:
                                    # 已经探索过了，准备起飞
                                    self.dest = None
                                    self.game.log.info(f"Robot {player.object_id} 准备起飞。")
                                    actions.append({
                                        "action": PlayerAction.TAKEOFF,
                                        "player_id": player.object_id,
                                    })
                            else:
                                # 还没降落，准备降落
                                self.game.log.info(f"Robot {player.object_id} 尝试降落在星球 {world.world_config.world_id} : {world.object_id}上。")
                                actions.append({
                                    "action": PlayerAction.LAND,
                                    "player_id": player.object_id,
                                    "world_id": world.object_id,
                                })
                        else:
                            # 并没有到达表面，寻路有问题？
                            self.game.log.warn("寻路并未到达既定目标表面, 重新寻路")
                            self.dest = None
                    pass
                elif self.dest.type == "location":
                    # 之前的目标是坐标
                    pass
                else:
                    pass

        else:
            # 已经完成了之前规划的路线， 开始选择移动目标
            planets_to_explore = self.select_planet_to_explore()
            if planets_to_explore:
                for planet in planets_to_explore:
                    self.game.log.info(
                        f"Robot {player.object_id} 考虑前往类型为{planet.world_config.world_id}的星球 {planet.object_id},坐标({planet.location}...")

                    # 获取星球表面的一个可用坐标
                    end_location = planet.get_spawn_location()
                    if not end_location:
                        self.game.log.warn(
                            f"Robot {player.object_id} 无法找到星球 {planet.object_id} 的可到达位置, 跳过该星球。")
                        continue

                    # 尝试寻路
                    start_location = player.fleet.location
                    path = self.game.pathfinder.find_path(
                        start_location,
                        end_location,
                        target_type="world",
                        target_world_id=planet.object_id
                    )

                    if path == []:
                        # 情况 1: 已经到达星球表面
                        self.dest = Dest(type="world", value=planet.object_id)
                        self.game.log.info(f"Robot {player.object_id} 已经位于星球 {planet.object_id} 表面，无需移动，准备降落。")
                        break
                    elif path:
                        # 情况 2: 找到路径
                        self.dest = Dest(type="world", value=planet.object_id)
                        self.game.log.info(f"Robot {player.object_id} 选择 前往类型为{planet.world_config.world_id}的星球 {planet.object_id}，并找到了路径。")
                        actions.append({
                            "action": PlayerAction.MOVE,
                            "path": path,
                            "travel_method": TravelMethod.SLOWTRAVEL,  # 寻路找到路径，肯定是慢速旅行
                            "player_id": player.object_id
                        })
                        break
                    else:
                        # 情况 3: 无法找到路径
                        self.game.log.warn(f"Robot {player.object_id} 无法找到前往星球 {planet.object_id} 的路径,尝试下一个星球。")
                        continue
                if not self.dest:
                    self.game.log.warn(f"Robot {player.object_id} 已遍历所有目标星球，所有目标都无法到达。")
            else:
                self.game.log.warn(f"Robot {player.object_id} 没有找到合适的移动目标。")

 
        # 处理事件
        event_action = self.handle_event()
        if event_action:
            self.game.log.info(f"Robot {player.object_id} 选择处理事件: ")
            actions.append(event_action)

        # 尝试升级
        building_instance = self.select_building_to_upgrade()
        if building_instance:
            self.game.log.info(f"Robot {player.object_id} 选择升级建筑: {building_instance.building_config.name_id}")
            actions.append({
                "action": PlayerAction.UPGRADE,
                "building_id": building_instance.object_id,
                "player_id": player.object_id
            })

        # 尝试建造
        explored_planets = [self.game.world_manager.get_world_by_id(pid) for pid in player.explored_planets]
        available_planets = [p for p in explored_planets if p]
        if available_planets:
            available_planets.sort(key=self.evaluate_planet, reverse=True)
            self.game.log.info(f"Robot {player.object_id} 正在评估可建造星球...")
            for planet in available_planets:
                building_config = self.select_building_to_build(planet)
                if building_config:
                    #还有可以建造的建筑(1级)
                    self.game.log.info(f"Robot {player.object_id} 选择在类型为{planet.world_config.world_id}的星球 {planet.object_id} 上建造建筑 {building_config.config_id}")
                    actions.append({
                        "action": PlayerAction.BUILD,
                        "planet_id": planet.object_id,
                        "building_config_id": building_config.config_id,
                        "player_id": player.object_id
                    })

        return actions

    def tick(self, game):
        """Robot 的 tick 方法，调用 think 并返回操作数据"""
        return self.think()