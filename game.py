from basic_types.basic_typs import Vector3
from basic_types.resource import Resource
from loader.locale import Locale
from basic_types.enums import *
from logger import Log
import logging
from time import sleep

class Game:
    def __init__(self):
        self.building_manager = None
        self.event_manager = None
        self.modifier_manager = None
        self.world_manager = None
        self.player_manager = None
        self.rule_manager = None
        self.purchase_manager = None
        self.message_bus = None
        self.robot = None
        self.tick_counter = 0
        self.log = Log(level=logging.DEBUG, filename="log.txt")
        self.path_finder = None

    def add_robot(self, resources, building_configs, purchase_configs):
        player = self.player_manager.create_player(resources, building_configs, purchase_configs)
        for resource in player.resources:
            player.resources[resource] = 10
        self.robot = self.player_manager.add_robot(player)

    def generate_worlds(self, num_worlds: int):
        """生成指定数量的星球"""

        # --- 参数设置 (可调整) ---
        density_factor = 50  # 密度因子：控制星球之间的平均距离。增大该值会使星球更稀疏。
        min_reachable_half_extent = 1  # 星球可到达区域的最小半边长（单元格数）
        max_reachable_half_extent = 10  # 星球可到达区域的最大半边长（单元格数）
        impenetrable_ratio_min = 0.1  # 星球不可穿透区域占可到达区域的最小比例
        impenetrable_ratio_max = 0.3  # 星球不可穿透区域占可到达区域的最大比例
        max_attempts = 100  # 生成每个星球的最大尝试次数

        # --- 参数设置结束 ---

        world_configs = self.world_manager.world_configs
        world_ids = list(world_configs.keys())
        probabilities = [world_configs[world_id].info['occur'] for world_id in world_ids]

        # 1. 动态计算空间大小
        total_half_extent = 0
        for world_id in world_ids:
            world_config = world_configs[world_id]
            avg_half_extent = (min_reachable_half_extent + max_reachable_half_extent) / 2
            total_half_extent += avg_half_extent * world_config.info['occur']
        average_half_extent = total_half_extent / sum(probabilities)
        average_volume = (2 * average_half_extent) ** 3
        side_length = int((density_factor * num_worlds * average_volume) ** (1/3))
        max_coord = side_length // 2

        generated_world_ids = set()  # 存储已生成的星球 ID
        for _ in range(num_worlds):
            for attempt in range(max_attempts):
                # 2. 随机选择星球类型
                selected_world_id = random.choices(world_ids, weights=probabilities)[0]
                world_config = world_configs[selected_world_id]

                # 3. 随机生成星球大小
                reachable_half_extent = random.randint(min_reachable_half_extent, max_reachable_half_extent)
                impenetrable_half_extent = int(reachable_half_extent * random.uniform(impenetrable_ratio_min, impenetrable_ratio_max))

                # 4. 随机生成位置
                location = Vector3(
                    random.randint(-max_coord, max_coord),
                    random.randint(-max_coord, max_coord),
                    random.randint(-max_coord, max_coord),
                )

                # 5. 调用 WorldManager 生成单个星球
                world = self.world_manager.generate_world(
                    world_config, location, reachable_half_extent, impenetrable_half_extent
                )

                # 6. 检查是否成功生成 (如果没有碰撞)
                if world:
                    generated_world_ids.add(world.object_id)

                    # 7. 初始化建筑
                    self.building_manager.add_world_slots(world.object_id, world.building_slots)
                    self.building_manager.add_world_buildings(world.object_id, self.world_manager._generate_initial_buildings(world.world_config))
                    break  # 成功生成，跳出尝试循环
            else:
                # 如果达到最大尝试次数，则放弃生成该星球
                print(f"Warning: Could not generate world after {max_attempts} attempts.")
            
    def run(self):
        last_time = datetime.datetime.now()
        while True:
            self.tick_counter += 1  # 增加总tick计数
            self.event_manager.tick() 
            self.player_manager.tick() 
            self.building_manager.tick() 
            self.modifier_manager.tick() 
            self.rule_manager.tick()
            self.message_bus.tick()

            now = datetime.datetime.now()
            elapsed =(now - last_time).seconds
            # 以下是为了管理员查看方便
            if elapsed >= 15:
                last_time = now
                elapsed = 0
                self.log.info("-------------------------------------------")
                self.log.info("当前资源：")
                for resource, amount in self.robot.resources.items():
                    self.log.info(f"{Locale.get_text(Resource.get_resource_by_id(resource).name_id)}: {amount}")

                self.log.info("已探索的星球及建筑：")
                for planet_id in self.robot.explored_planets:
                    planet = self.world_manager.get_world_by_id(planet_id)
                    planet_name = Locale.get_text(planet.world_config.world_id)
                    self.log.info(f"星球{planet_id}: {planet_name} ({planet.location})")
                    for building_instance in self.building_manager.get_buildings_on_world(planet_id):
                        building_name = Locale.get_text(building_instance.building_config.name_id)
                        building_level = building_instance.building_config.level
                        if building_instance.remaining_secs > 0:
                            self.log.info(f"  - 建筑{building_instance.object_id}: {building_name}, 等级:{building_level}" + "(建造/升级中)")
                        else:
                            self.log.info(f"  - 建筑{building_instance.object_id}: {building_name}, 等级:{building_level}")
                self.log.info("-------------------------------------------")

                # 打印管理器状态
                self.log.info("############################################")
                self.log.info(f"  WorldManager: 管理星球数量 = {len(self.world_manager.world_instances)}")
                self.log.info(f"  BuildingManager: 管理建筑数量 = {len(self.building_manager.building_instances)}")
                self.log.info(f"  PlayerManager: 管理玩家数量 = {len(self.player_manager.players)}, 管理机器人数量: {len(self.player_manager.robots)}")
                self.log.info(f"  EventManager: 活跃事件数量 = {sum(len(events) for events in self.event_manager.active_events.values())}")
                self.log.info(f"  ModifierManager: 活跃 Modifier 数量 = {len(self.modifier_manager.modifiers)}")
                self.log.info(f"  MessageBus: 消息队列长度 = {len(self.message_bus.messages)}, 待处理消息数量 = {len(self.message_bus.pending_messages)}")
                self.log.info(f"  Pathfinder: 缓存路径数量: {len(self.path_finder._path_cache)}")
                self.log.info("############################################")    
