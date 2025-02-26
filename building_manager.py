from loader.building_config import BuildingConfig
from loader.enums import Modifier

class BuildingInstance:
    def __init__(self, building_config: BuildingConfig, remaining_rounds=3):
        self.building_config = building_config
        self.remaining_rounds = remaining_rounds

    def start_construction(self):
        pass

    def check_completion(self):
        if self.remaining_rounds > 0:
            self.remaining_rounds -= 1
            return False
        return True

class UpgradeInstance:
    def __init__(self, old_building: BuildingConfig, new_building: BuildingConfig, remaining_rounds=3):
        self.old_building = old_building
        self.new_building = new_building
        self.remaining_rounds = remaining_rounds

    def check_completion(self):
        if self.remaining_rounds > 0:
            self.remaining_rounds -= 1
            return False
        return True

class BuildingManager:
    def __init__(self, all_buildings):
        self.all_buildings = all_buildings
        self.player_buildings = {}  # 存储每个玩家的建筑，格式为 {player: [building1, building2, ...]}

    def get_next_level_building(self, building: BuildingConfig):
        """
        获取建筑的下一级建筑
        """
        next_level_id = building.get_next_level_id()
        return self.all_buildings.get(next_level_id)

    def build_cost_check(self, player, building):
        for resource_id, modifier_dict in building.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == Modifier.USE:
                    if player.resources.get(resource_id, 0) < quantity:
                        return False
        return True

    def build_cost_apply(self, player, building):
        for resource_id, modifier_dict in building.modifiers.items():
            for modifier, quantity in modifier_dict.items():
                if modifier == Modifier.USE:
                    player.resources[resource_id] -= quantity

    def upgrade_cost_check(self, player, building):
        return building.can_upgrade(player.resources, self.all_buildings)

    def upgrade_cost_apply(self, player, building):
        upgrade_cost = building.get_upgrade_cost(self.all_buildings)
        for resource_id, quantity in upgrade_cost.items():
            player.resources[resource_id] -= quantity

    def build_building(self, player, planet, building):
        if player.can_build_on_slot(planet, building) and self.build_cost_check(player, building):
            self.build_cost_apply(player, building)
            if player not in self.player_buildings:
                self.player_buildings[player] = []
            building_instance = BuildingInstance(building)
            building_instance.remaining_rounds = building.build_period
            self.player_buildings[player].append(building_instance)
            return True
        return False

    def upgrade_building(self, player, planet, building):
        next_level_building = self.get_next_level_building(building)
        if player.can_upgrade_building(planet, building) and self.upgrade_cost_check(player, building):
            self.upgrade_cost_apply(player, building)
            index = self.player_buildings[player].index(building)
            upgrade_instance = UpgradeInstance(building, next_level_building)
            upgrade_instance.remaining_rounds = next_level_building.build_period
            self.player_buildings[player][index] = upgrade_instance
            return True
        return False

    def tick(self):
        """
        更新建筑状态和处理资源产出
        """
        for player, buildings in self.player_buildings.items():
            for building in buildings[:]:
                if isinstance(building, (BuildingInstance, UpgradeInstance)) and building.remaining_rounds > 0:
                    building.remaining_rounds -= 1
                    if building.remaining_rounds == 0:
                        # 建筑建设或升级完成
                        if isinstance(building, BuildingInstance):
                            print(f"建筑 {building.building_config.name_id} 建设完成")
                            # 更新星球建筑列表
                            planet = player.fleet["planet"]
                            planet_buildings = player.planets_buildings.get(planet.world_config.world_id, [])
                            planet_buildings.append(building.building_config)
                        elif isinstance(building, UpgradeInstance):
                            print(f"建筑 {building.old_building.name_id} 升级完成")
                            # 更新星球建筑列表
                            planet = player.fleet["planet"]
                            planet_buildings = player.planets_buildings.get(planet.world_config.world_id, [])
                            index = planet_buildings.index(building.old_building)
                            planet_buildings[index] = building.new_building
                else:
                    # 建筑已完成，处理资源产出
                    if isinstance(building, BuildingInstance):
                        for resource_id, modifier_dict in building.building_config.modifiers.items():
                            for modifier, quantity in modifier_dict.items():
                                if modifier == Modifier.PRODUCTION:
                                    # 根据耐久度计算实际产出
                                    durability_ratio = building.building_config.durability / building.building_config.max_durability
                                    production_amount = quantity * durability_ratio
                                    player.resources[resource_id] = player.resources.get(resource_id, 0) + production_amount
