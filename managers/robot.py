from basic_types.enums import *
from basic_types.resource import Resource
from common import *
import heapq

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
                avaliable = player.resources.get(resource, 0)
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
        """选择要在指定星球上建造的建筑 (改进版)"""
        player = self.game.player_manager.get_player_by_id(self.object_id)
        available_buildings = []

        for config_id, building_config in player.avaliable_building_config.items():
            if self.can_build_on_slot(planet, building_config):
                available_buildings.append(building_config)

        if not available_buildings:
            return None

        # 优先选择 1 级建筑
        level_1_buildings = [b for b in available_buildings if b.level == 1]
        if not level_1_buildings:
            return None  # 没有 1 级建筑，无法建造

        # --- 资源建筑优先级 ---
        key_resource_buildings = [
            b for b in level_1_buildings
            if any(
                modifier_config.data_type in ("resource.promethium")  # 关键资源
                for modifier_config in b.modifier_configs
                if modifier_config.modifier_type == ModifierType.PRODUCTION
            )
        ]
        if key_resource_buildings:
            return random.choice(key_resource_buildings)

        resource_buildings = [
            b for b in level_1_buildings
            if b.type == BuildingType.RESOURCE and not any(
                modifier_config.data_type in ("resource.promethium")
                for modifier_config in b.modifier_configs
                if modifier_config.modifier_type == ModifierType.PRODUCTION
            )
        ]
        if resource_buildings:
            return random.choice(resource_buildings)

        # --- General 建筑选择 ---
        general_buildings = [b for b in level_1_buildings if b.type == BuildingType.GENERAL]
        if general_buildings:
            # 人口阈值 (示例：75%)
            population_threshold = 0.75 * player.resources.get(Resource.get_resource_by_id("resource.population"), 0)

            if player.available_manpower < population_threshold:
                # 人口不足，优先人口建筑
                population_buildings = [
                    b for b in general_buildings
                    if any(modifier.data_type == "resource.population"
                           for modifier in b.modifier_configs
                           if modifier.modifier_type == ModifierType.PRODUCTION)
                ]
                if population_buildings:
                    return random.choice(population_buildings)

            # 达到人口阈值，或没有可用的人口建筑，考虑配额
            # (简化实现：只在人口充足时才建造其他 General 建筑)
            if player.available_manpower >= population_threshold:
                # 随机选择 (TODO: 未来可以根据配额更智能地选择)
                return random.choice(general_buildings)
            else:
                return None

        # --- 其他情况 ---
        return random.choice(level_1_buildings)  # 兜底
        
    def calculate_building_upgrade_benefit(self, building_instance):
        """计算建筑升级的收益 (考虑多种升级路径和资源稀缺度)"""
        player = self.game.player_manager.get_player_by_id(self.object_id)
        total_benefit = 0

        # 获取所有可能的下一级建筑配置
        next_level_configs = []
        for config_id, config in self.game.building_manager.building_configs.items():
            if (config.type == building_instance.building_config.type and
                config.subtype == building_instance.building_config.subtype and
                config.level == building_instance.building_config.level + 1):
                next_level_configs.append(config)

        if not next_level_configs:
            return 0  # 没有下一级建筑

        for next_config in next_level_configs:
            benefit = 0
            best_choice = (0, next_config)
            # 计算产出变化
            for modifier in next_config.modifier_configs:
                if modifier.modifier_type == ModifierType.PRODUCTION:
                    resource_id = modifier.data_type
                    # 获取当前建筑对应资源的产出 (如果没有则为 0)
                    current_production = 0
                    for current_modifier in building_instance.building_config.modifier_configs:
                        if (current_modifier.modifier_type == ModifierType.PRODUCTION and
                            current_modifier.data_type == resource_id):
                            current_production = current_modifier.quantity
                            break

                    production_change = modifier.quantity - current_production

                    # 计算资源权重 (越稀缺权重越高)
                    resource_amount = player.resources.get(resource_id, 1)  # 获取资源数量，默认为1避免除以0
                    resource_weight = 1 / resource_amount if resource_amount>0 else 100 #资源为0的时候给一个极高的权重

                    benefit += production_change * resource_weight

                # 计算消耗变化 (可选，如果您希望考虑升级带来的消耗增加)
                elif modifier.modifier_type == ModifierType.CONSUME:
                    resource_id = modifier.data_type
                    # 获取当前建筑对应资源的消耗
                    current_consumption = 0
                    for current_modifier in building_instance.building_config.modifier_configs:
                        if (current_modifier.modifier_type == ModifierType.CONSUME and
                            current_modifier.data_type == resource_id):
                            current_consumption = current_modifier.quantity
                            break

                    consumption_change = modifier.quantity - current_consumption
                    resource_amount = player.resources.get(resource_id, 1)
                    resource_weight = 1 / resource_amount if resource_amount>0 else 100

                    benefit -= consumption_change * resource_weight  # 消耗增加是负收益

            total_benefit += benefit
        if total_benefit > best_choice[0]:
            best_choice = (total_benefit, next_config)

        return best_choice

    def select_building_to_upgrade(self):
        """选择要升级的建筑 (改进版)"""
        player = self.game.player_manager.get_player_by_id(self.object_id)
        upgradeable_buildings = []

        for planet_id in player.explored_planets:
            for building_instance in self.game.building_manager.get_buildings_on_world(planet_id):
                # 获取下一级建筑配置
                next_level_building_configs = self.game.building_manager.get_next_level_configs(building_instance.building_config)
                if len(next_level_building_configs) >0 :
                    # 检查资源是否足够
                    for next_level_building_config in next_level_building_configs:
                        can_afford = self.can_afford_building_cost(player, next_level_building_config)
                        if can_afford:
                            if building_instance not in upgradeable_buildings:
                                upgradeable_buildings.append(building_instance) 

        if not upgradeable_buildings:
            return None, None

        # 根据收益选择要升级的建筑
        best_building = None
        best_benefit = (-1, None)

        for building_instance in upgradeable_buildings:
            benefit = self.calculate_building_upgrade_benefit(building_instance)
            if benefit[0] > best_benefit[0]:
                best_benefit = benefit
                best_building = building_instance

        return best_building, best_benefit[1] # 如果没有值得升级的建筑，则返回 None

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
    
    def purchase_rare_resources(self):
            """尝试购买稀有资源"""
            player = self.game.player_manager.get_player_by_id(self.object_id)
            if not player:
                return None

            # 检查稀有资源是否少于阈值
            for resource_id, amount in player.resources.items():
                resource = Resource.get_resource_by_id(resource_id)
                if resource and resource.type == ResourceType.RARE:
                    if amount < 5:
                        self.game.log.info(f"Robot {player.object_id} 发现稀有资源 {resource.name_id} 不足，尝试购买。")
                        return {
                            "action": PlayerAction.PURCHASE,
                            "player_id": player.object_id,
                            "name": "resource_purchase_package_lvl1",
                            "quantity": 1,
                        }
            return None
    
    def calculate_building_priority(self, building_instance, player):
        """计算建筑的优先级"""
        priority = 0

        # 建筑类型
        if building_instance.building_config.type == BuildingType.RESOURCE:
            priority += 100
        elif building_instance.building_config.type == BuildingType.GENERAL:
            priority += 50

        # 建筑等级
        priority += building_instance.building_config.level * 10

        # 人力比例 (当前人力/最大人力，比例越低，优先级越高)
        manpower_ratio = building_instance.manpower / building_instance.building_config.manpower if building_instance.building_config.manpower >0 else 0
        priority += (1 - manpower_ratio) * 20  # 转换为优先级，所以用 1 减

        # (可选) 资源稀缺度
        # for modifier in building_instance.building_config.modifier_configs:
        #     if modifier.modifier_type == ModifierType.PRODUCTION:
        #         resource_amount = player.resources.get(modifier.data_type, 1)
        #         resource_weight = 1 / resource_amount  # 简化计算
        #         priority += resource_weight * 5

        return priority

    def allocate_manpower(self):
        """分配人力 (全局视角)"""
        player = self.game.player_manager.get_player_by_id(self.object_id)
        if player.available_manpower <= 0:
            return None

        building_queue = []  # 优先级队列 (-priority, building_id, building_instance)

        for world_id in player.explored_planets:
            world = self.game.world_manager.get_world_by_id(world_id)
            if not world:
                continue

            for building_instance in self.game.building_manager.get_buildings_on_world(world_id):
                if building_instance.manpower < building_instance.building_config.manpower:
                    priority = self.calculate_building_priority(building_instance, player)
                    heapq.heappush(building_queue, (-priority, building_instance.object_id, building_instance))

        actions = []
        available_manpower = player.available_manpower  # 创建本地副本

        while building_queue and available_manpower > 0:  # 使用本地副本
            _, _, building_instance = heapq.heappop(building_queue)  # 取出时忽略 building_id
            delta = building_instance.building_config.manpower - building_instance.manpower
            allocate_count = min(available_manpower, delta)  # 使用本地副本

            actions.append({
                "action": PlayerAction.ALLOCATE_MANPOWER,
                "player_id": player.object_id,
                "building_id": building_instance.object_id,
                "amount": allocate_count,
            })
            available_manpower -= allocate_count  # 更新本地副本

        return actions if actions else None

    def think(self):
        """模拟玩家思考并返回行动"""
        now = datetime.datetime.now()
        #if (now - self.last_think).seconds <=1 :
        #    return
        
        self.last_think = now
        actions = []
        player = self.game.player_manager.get_player_by_id(self.object_id)
        self.game.log.info(f"Robot {player.object_id} 开始思考...")

        # 检查舰队移动状态
        if self.dest is not None:
            # 有已经规划的路线
            if len(player.fleet.path)>0:
                # 尚未到达，继续移动
                self.game.log.info(f"Robot {player.object_id} 的舰队正在移动中, 下个目标{player.fleet.path[0]}")
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
                    end_location = planet.get_spawn_location()
                    if not end_location:
                        self.game.log.warn(
                            f"Robot {player.object_id} 无法找到星球 {planet.object_id} 的可到达位置, 跳过该星球。")
                        continue

                    self.game.log.info(
                        f"Robot {player.object_id} 考虑前往类型为{planet.world_config.world_id}的星球 {planet.object_id},中心坐标({planet.location}, 当前坐标{player.fleet.location} , 目的坐标{end_location}...")

                    # 获取星球表面的一个可用坐标

                    # 尝试寻路
                    start_location = player.fleet.location
                    path = self.game.path_finder.find_path(
                        start_location,
                        end_location,
                        player.fleet.travel_speed
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
        building_instance, next_level_building_config = self.select_building_to_upgrade()
        if building_instance:
            self.game.log.info(f"Robot {player.object_id} 选择升级建筑: {building_instance.building_config.name_id} 为{next_level_building_config.name_id}")
            actions.append({
                "action": PlayerAction.UPGRADE,
                "building_id": building_instance.object_id,
                "player_id": player.object_id,
                "building_config_id": next_level_building_config.config_id,
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
        # 尝试分配人力
        manpower_action = self.allocate_manpower()
        if manpower_action:
            actions.extend(manpower_action)

        # 尝试购买稀有资源
        player = self.game.player_manager.get_player_by_id(self.object_id)
        if player.available_purchases:  # 检查是否有可购买项
            purchase_action = self.purchase_rare_resources()
            if purchase_action:
                self.game.log.info(f"Robot {player.object_id} 决定购买稀有资源。")
                actions.append(purchase_action)

        return actions

    def tick(self, game):
        """Robot 的 tick 方法，调用 think 并返回操作数据"""
        return self.think()