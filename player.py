import random
from typing import Dict
from loader.building_config import BuildingConfig


class Player:
    def __init__(self, resources: Dict[str, float]):
        self.resources = {resource_id: 0 for resource_id in resources.keys()}
        self.fleet = {
            "morale": 100,
            "attack": 50,
            "defense": 50,
            "planet": None
        }
        self.avaliable_building_config = []
        self.characters = [{"name": "角色 1", "location": None}]
        self.explored_planets = []  # 维护已探索星球对象
        self.planets_buildings = {}  # 管理各个星球上的建筑实例
        self.constructing_buildings = []  # 管理正在建造的建筑实例的索引
        self.upgrading_buildings = []  # 管理正在升级的建筑实例的索引

    def think(self):
        actions = ['move', 'build', 'command']
        return random.choice(actions)

    def set_avaliable_buildings(self, building_config):
        self.avaliable_building_config = building_config

    def can_build_on_slot(self, planet, building):
        """
        检查是否可以在星球的空格上建造该建筑
        """
        buildings = self.planets_buildings.get(planet.world_config.world_id, [])
        slot_type = building.subtype.name.lower()
        available_slots = planet.resource_slots.get(slot_type, 0)
        built_buildings = [b for b in buildings if b.subtype == building.subtype]
        if len(built_buildings) >= available_slots:
            return False
        return building.level == 1

    def can_upgrade_building(self, planet, building):
        """
        检查建筑是否可以升级
        """
        buildings = self.planets_buildings.get(planet.world_config.world_id, [])
        if building not in buildings:
            return False
        return building.can_upgrade(self.resources, self.buildings)

    def select_building_to_build(self, planet):
        buildable_buildings = [b for b in self.avaliable_building_config.values() if self.can_build_on_slot(planet, b)]
        if buildable_buildings:
            return random.choice(buildable_buildings)
        return None

    def select_building_to_upgrade(self, planet):
        buildings = self.planets_buildings.get(planet.world_config.world_id, [])
        upgradable_buildings = [b for b in buildings if self.can_upgrade_building(planet, b)]
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

    def start_building(self, building_config: BuildingConfig, planet, building_manager):
        if building_manager.build_building(self, planet, building_config):
            # 初始化星球的建筑列表
            if planet.world_config.world_id not in self.planets_buildings:
                self.planets_buildings[planet.world_config.world_id] = []
            building_index = len(building_manager.player_buildings[self]) - 1
            self.constructing_buildings.append(building_index)
            return building_index
        return None

    def start_upgrade(self, old_building_config: BuildingConfig, new_building_config: BuildingConfig, planet, building_manager):
        if building_manager.upgrade_building(self, planet, old_building_config):
            index = building_manager.player_buildings[self].index(old_building_config)
            self.upgrading_buildings.append(index)
            return index
        return None

    def check_building_completion(self, building_manager):
        completed_buildings = []
        for building_index in self.constructing_buildings[:]:
            building = building_manager.player_buildings[self][building_index]
            if building.check_completion():
                completed_buildings.append(building)
                # 假设建筑完成后添加到星球建筑列表
                planet = self.fleet["planet"]
                if planet:
                    if planet.world_config.world_id not in self.planets_buildings:
                        self.planets_buildings[planet.world_config.world_id] = []
                    self.planets_buildings[planet.world_config.world_id].append(building.building_config)
                self.constructing_buildings.remove(building_index)
        return completed_buildings

    def check_upgrade_completion(self, building_manager):
        completed_upgrades = []
        for building_index in self.upgrading_buildings[:]:
            building = building_manager.player_buildings[self][building_index]
            if building.check_completion():
                completed_upgrades.append(building)
                # 假设升级完成后更新星球建筑列表
                planet = self.fleet["planet"]
                if planet:
                    buildings = self.planets_buildings.get(planet.world_config.world_id, [])
                    index = buildings.index(building.old_building)
                    buildings[index] = building.new_building
                self.upgrading_buildings.remove(building_index)
        return completed_upgrades
