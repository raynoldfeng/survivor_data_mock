# robot.py
import random
from typing import Optional
from loader.building_config import BuildingConfig
from managers.world_manager import World
from managers.player_manager import Player


class Robot:
    def __init__(self, player: "Player", game):
        self.player: "Player" = player
        self.game = game

    def think(self) -> dict:
        """AI思考并决定下一步行动，返回包含行动类型和参数的字典"""
        actions = ['move', 'build', 'upgrade']
        chosen_action = random.choice(actions)

        if chosen_action == 'move':
            target_planet = self.select_target_planet()
            if target_planet:
                return {
                    'action': 'move',
                    'target_planet_id': target_planet.object_id
                }
            else:  # 如果没有可移动的目标星球，则改为其他行动
                return self.think()  # 重新思考

        elif chosen_action == 'build':
            planet = self.game.world_manager.find_by_id(self.player.fleet.location)
            
            if planet:
                building_to_build = self.select_building_to_build(planet)
                if building_to_build:
                    return {
                        'action': 'build',
                        'planet_id': planet.object_id,
                        'building_id': building_to_build.building_id
                    }
                else:  # 如果当前星球不能建造，则改为其他行动
                    return self.think()
            else:
                return self.think()

        elif chosen_action == 'upgrade':
            planet = self.game.world_manager.find_by_id(self.player.fleet.location)
            if planet:
                building_to_upgrade = self.select_building_to_upgrade(planet)
                if building_to_upgrade:
                    return {
                        'action': 'upgrade',
                        'building_id': building_to_upgrade.object_id  # 使用 object_id
                    }
                else:  # 如果当前星球没有可升级建筑，则改为其他行动
                    return self.think()
            else:
                return self.think()


    def can_build_on_slot(self, planet: "World", building: "BuildingConfig") -> bool:
        """检查是否可以在星球的空格上建造该建筑"""
        buildings = self.game.building_manager.get_buildings_on_world(planet)
        slot_type = building.subtype.name.lower()
        available_slots = planet.resource_slots.get(slot_type, 0)
        built_buildings = [b for b in buildings if b.building_config.subtype == building.subtype]
        if len(built_buildings) >= available_slots:
            return False
        return building.level == 1

    def can_upgrade_building(self, planet: "World", building: "BuildingConfig") -> bool:
        """检查建筑是否可以升级"""
        buildings = self.game.building_manager.get_buildings_on_world(planet)
        if building.object_id not in [b.object_id for b in buildings]:
            return False
        return building.can_upgrade(self.player.resources, self.game.building_manager.building_configs)

    def select_building_to_build(self, planet: "World") -> Optional["BuildingConfig"]:
        """选择要建造的建筑"""
        buildable_buildings = [b for b in self.player.avaliable_building_config.values() if
                                 self.can_build_on_slot(planet, b)]
        if buildable_buildings:
            return random.choice(buildable_buildings)
        return None

    def select_building_to_upgrade(self, planet: "World") -> Optional["BuildingConfig"]:
        """选择要升级的建筑"""
        buildings = self.game.building_manager.get_buildings_on_world(planet)
        upgradable_buildings = [b.building_config for b in buildings if
                                 self.can_upgrade_building(planet, b.building_config)]
        if upgradable_buildings:
            return random.choice(upgradable_buildings)
        return None

    def select_target_planet(self) -> Optional["World"]:
        """选择目标星球"""
        if self.player.explored_planets:
            return random.choice(self.player.explored_planets)
        return None