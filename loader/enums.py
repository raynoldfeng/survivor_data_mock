from .imports import *
# 资源类型枚举
class ResourceType(Enum):
    PRIMARY = "Primary"    # 基础资源 (原生资源)
    SECONDARY = "Secondary"  # 次生资源
    RARE = "Rare"         # 稀有资源

# 建筑类型枚举
class BuildingType(Enum):
    RESOURCE = "Resource"  # 资源采集建筑
    GENERAL = "General"    # 通用建筑
    DEFENSE = "Defense"    # 防御建筑

# 建筑子类型枚举 (根据建筑类型细分)
class ResourceSubType(Enum):
    ADAMANTIUM = "Adamantium"
    PLASTEEL = "Plasteel"
    CERAMITE = "Ceramite"
    PROMETHIUM = "Promethium"
    PROMETHAZINE = "Promethazine"
    FARM = "Farm"           

class GeneralSubType(Enum):
    HABITATION = "Habitation"  # 居民点 (包括城市、教堂、大教堂)
    WORKSHOP = "Workshop"      # 工作坊 (包括加工厂、铸造工厂、兵工厂、高级武器工厂)
    LABORATORY = "Laboratory"  # 实验室 (包括化工厂、高级化工厂、研究所、STC研究所)

class DefenseSubType(Enum):
    ORBITALDEFENSE = "OrbitalDefense"  # 轨道防御
    ENERGYSHIELD = "EnergyShield"    # 能量护盾
    PSYCHICBARRIER = "PsychicBarrier" # 灵能屏障
    GROUNDFORTRESS = "GroundFortress"  # 地面堡垒
    
# 防御类型枚举
class DefenseType(Enum):
    ORBITAL = "Orbital"    # 轨道
    ENERGY = "Energy"      # 能量
    PSYCHIC = "Psychic"    # 灵能
    GROUND = "Ground"      # 地表

class WorldType(Enum):
    GASEOUS_GIANT = "Gaseous Giant"
    ROCKY_PLANET = "Rocky Planet"
    ASTEROID = "Asteroid"

class RockyPlanetSubtype(Enum):
    LAVA = "Lava"
    DEATH = "Death"
    WOODLAND = "Woodland"
    DESERT = "Desert"
    OCEAN = "Ocean"
    FROZEN = "Frozen"

class Modifier(Enum):
    PRODUCTION = "Production"  # 单位时间产出
    COST = "Cost"  # 单位时间消耗
    INCREASE = "Increrase"  # 一次性增加
    REDUCE = "Reduce"  # 一次性扣除

class Target(Enum):
    PLANET = "Planet"
    BUILDING = "Building"
    FLEET = "Fleet"
    RESOURCES = "Resources"
    CHARACTER = "Character"  # 若后续有角色相关的事件主体可使用该枚举值