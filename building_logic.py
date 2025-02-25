from loader.building import Building
from loader.enums import Modifier

def can_build_on_slot(planet, building, planet_buildings):
    """
    检查是否可以在星球的空格上建造该建筑
    """
    slot_type = building.subtype.name.lower()
    available_slots = planet.resource_slots.get(slot_type, 0)
    built_buildings = [b for b in planet_buildings if b.subtype == building.subtype]
    if len(built_buildings) >= available_slots:
        return False
    return building.level == 1

def can_upgrade_building(planet, building, planet_buildings, all_buildings):
    """
    检查建筑是否可以升级
    """
    if building not in planet_buildings:
        return False
    next_level_building = get_next_level_building(building, all_buildings)
    if next_level_building is None:
        return False
    for resource_id, modifier_dict in next_level_building.modifiers.items():
        for modifier, quantity in modifier_dict.items():
            if modifier == Modifier.USE:
                if player.resources.get(resource_id, 0) < quantity:
                    return False
    return True

def get_next_level_building(building: Building, all_buildings):
    """
    获取建筑的下一级建筑
    假设建筑 ID 按规则命名，如 building.resource.mine.level1 -> building.resource.mine.level2
    """
    current_level = building.level
    next_level = current_level + 1
    current_id_parts = building.building_id.split('.')
    current_id_parts[-1] = f"level{next_level}"
    next_level_id = '.'.join(current_id_parts)
    return all_buildings.get(next_level_id)

def build_cost_check(player, building):
    for resource_id, modifier_dict in building.modifiers.items():
        for modifier, quantity in modifier_dict.items():
            if modifier == Modifier.USE:
                if player.resources.get(resource_id, 0) < quantity:
                    return False
    return True

def build_cost_apply(player, building):
    for resource_id, modifier_dict in building.modifiers.items():
        for modifier, quantity in modifier_dict.items():
            if modifier == Modifier.USE:
                player.resources[resource_id] -= quantity

def upgrade_cost_check(player, next_level_building):
    for resource_id, modifier_dict in next_level_building.modifiers.items():
        for modifier, quantity in modifier_dict.items():
            if modifier == Modifier.USE:
                if player.resources.get(resource_id, 0) < quantity:
                    return False
    return True

def upgrade_cost_apply(player, next_level_building):
    for resource_id, modifier_dict in next_level_building.modifiers.items():
        for modifier, quantity in modifier_dict.items():
            if modifier == Modifier.USE:
                player.resources[resource_id] -= quantity