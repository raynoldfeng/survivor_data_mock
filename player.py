import random
from typing import Dict, List
from loader.building import Building
from building_logic import (
    can_build_on_slot,
    can_upgrade_building,
)

class BuildingInstance:
    def __init__(self, building_config: Building, remaining_rounds=3):
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
    def __init__(self, old_building: Building, new_building: Building, remaining_rounds=3):
        self.old_building = old_building
        self.new_building = new_building
        self.remaining_rounds = remaining_rounds

    def check_completion(self):
        if self.remaining_rounds > 0:
            self.remaining_rounds -= 1
            return False
        return True

class Player:
    def __init__(self, resources: Dict[str, float], worlds, buildings: Dict[str, Building]):
        self.resources = {resource_id: 0 for resource_id in resources.keys()}
        self.fleet = {
            "morale": 100,
            "attack": 50,
            "defense": 50,
            "planet": random.choice(worlds) if worlds else None
        }
        self.characters = [{"name": "角色 1", "location": self.fleet["planet"]}]
        self.buildings = buildings
        self.explored_planets = []  # 维护已探索星球对象
        self.planet_buildings = {world.world_config.world_id: [] for world in worlds}
        self.constructing_buildings: List[BuildingInstance] = []  # 管理正在建造的建筑实例
        self.upgrading_buildings: List[UpgradeInstance] = []  # 管理正在升级的建筑实例

    def think(self):
        actions = ['move', 'build', 'command']
        return random.choice(actions)

    def select_building_to_build(self, planet):
        planet_buildings = self.planet_buildings[planet.world_config.world_id]
        buildable_buildings = [b for b in self.buildings.values() if can_build_on_slot(planet, b, planet_buildings)]
        if buildable_buildings:
            return random.choice(buildable_buildings)
        return None

    def select_building_to_upgrade(self, planet):
        planet_buildings = self.planet_buildings[planet.world_config.world_id]
        upgradable_buildings = [b for b in planet_buildings if can_upgrade_building(planet, b, planet_buildings, self.buildings)]
        if upgradable_buildings:
            return random.choice(upgradable_buildings)
        return None

    def select_command(self):
        return random.choice(['build', 'upgrade'])

    def select_target_planet(self):
        if self.explored_planets:
            return random.choice(self.explored_planets)
        return None

    def move_to_planet(self, planet):
        self.fleet["planet"] = planet
        for character in self.characters:
            character["location"] = planet
        if planet not in self.explored_planets:
            rewards = planet.exploration_rewards
            for resource_id, quantity in rewards:
                self.explored_planets.append(planet)

    def start_building(self, building_config: Building, planet):
        building_instance = BuildingInstance(building_config)
        self.constructing_buildings.append(building_instance)
        return building_instance

    def start_upgrade(self, old_building: Building, new_building: Building, planet):
        upgrade_instance = UpgradeInstance(old_building, new_building)
        self.upgrading_buildings.append(upgrade_instance)
        return upgrade_instance

    def check_building_completion(self):
        completed_buildings = []
        for building_instance in self.constructing_buildings:
            if building_instance.check_completion():
                completed_buildings.append(building_instance)
                # 假设建筑完成后添加到星球建筑列表
                planet = self.fleet["planet"]
                self.planet_buildings[planet.world_config.world_id].append(building_instance.building_config)
        for completed_building in completed_buildings:
            self.constructing_buildings.remove(completed_building)
        return completed_buildings

    def check_upgrade_completion(self):
        completed_upgrades = []
        for upgrade_instance in self.upgrading_buildings:
            if upgrade_instance.check_completion():
                completed_upgrades.append(upgrade_instance)
                # 假设升级完成后更新星球建筑列表
                planet = self.fleet["planet"]
                planet_buildings = self.planet_buildings[planet.world_config.world_id]
                index = planet_buildings.index(upgrade_instance.old_building)
                planet_buildings[index] = upgrade_instance.new_building
        for completed_upgrade in completed_upgrades:
            self.upgrading_buildings.remove(completed_upgrade)
        return completed_upgrades