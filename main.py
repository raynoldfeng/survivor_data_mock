from loader.world import load_world_configs, create_world
from loader.resource import load_resources_from_csv
from loader.building import load_buildings_from_csv
from loader.locale import Locale
import random


# 加载资源数据
resources = load_resources_from_csv('resources/resources.csv')
# 加载建筑数据
buildings = load_buildings_from_csv('resources/buildings.csv')
# 加载多语言数据
Locale.load_from_csv('resources/locale_data.csv')
Locale.set_language("cn")

# 加载世界配置
world_configs = load_world_configs(
    world_info_file='resources/world_info.csv',
    world_init_structures_file='resources/world_init_structures.csv',
    world_explored_rewards_file='resources/world_explored_rewards.csv'
)

# 世界生成器函数
def world_generator(num_worlds, world_configs):
    worlds = []
    world_ids = list(world_configs.keys())
    for _ in range(num_worlds):
        # 随机选择一个世界配置
        random_world_id = random.choice(world_ids)
        world_config = world_configs[random_world_id]

        # 根据配置创建具体的世界对象
        world = create_world(world_config)
        worlds.append(world)
    return worlds

# 生成 100 个世界
worlds = world_generator(100, world_configs)

# 遍历打印世界信息
for world in worlds:
    # 探索世界
    world.explore_world()

    # 打印世界信息
    print(f"World ID: {world.world_config.world_id}")
    # 打印调整后的资源槽位
    print(f"Adjusted Resource Slots: {world.resource_slots}")
    # 打印实际生成的初始建筑
    print(f"Actual Initial Buildings: {world.actual_initial_buildings}")
    # 打印探索奖励
    print(f"Exploration Rewards: {world.exploration_rewards}")
    print("-" * 50)