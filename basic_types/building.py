from .building_config import BuildingConfig
from .base_object import BaseObject

class BuildingInstance(BaseObject):
    def __init__(self, building_config: BuildingConfig):
        super().__init__()
        self.building_config: BuildingConfig = building_config
        self.remaining_ticks: int = building_config.build_period 
        self.durability: int = building_config.durability
        self.is_under_attack: bool = False
        self.manpower : int = 0 #投入的人口数量，将影响产出

    def take_damage(self, damage: int):
        """受到伤害"""
        self.durability -= damage
        if self.durability <= 0:
            self.durability = 0
            # 发送建筑被摧毁的消息 (在tick中处理)

    def get_destroyed(self) -> bool:
        """获取是否被摧毁"""
        return self.durability <= 0
