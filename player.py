import random
from typing import Dict
from loader.building import *
from building_logic import *
from building_instance import *

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
        self.constructing_buildings = []  # 管理正在建造的建筑实例

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
                self.resources[resource_id] = self.resources.get(resource_id, 0) + quantity
            self.explored_planets.append(planet)

    def start_building(self, building_config: Building, planet):
        if build_cost_check(self, building_config):
            build_cost_apply(self, building_config)
            building_instance = BuildingInstance(building_config)
            building_instance.start_construction()
            self.constructing_buildings.append(building_instance)
            return building_instance
        return None

    def check_building_completion(self):
        completed_buildings = []
        for building_instance in self.constructing_buildings:
            if building_instance.check_completion():
                completed_buildings.append(building_instance)
        for completed_building in completed_buildings:
            self.constructing_buildings.remove(completed_building)
        return completed_buildings