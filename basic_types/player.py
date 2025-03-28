from basic_types.basic_typs import *
from basic_types.enums import ObjectType
from common import *
from .resource import Resource
from .base_object import BaseObject

class Fleet:
    def __init__(self):
        self.morale = 100
        self.attack = 50
        self.defense = 50
        self.path = []
        self.travel_start_round = 0
        self.travel_speed = 1.0 # 现在速度的单位是 cell/tick
        self.travel_method = None
        self.landed_on = None
        self.location = Vector3(0,0,0) # 单元格坐标

    def set_path(self, path: List[Vector3]):
        """设置路径"""
        self.path = path

    def set_travel_method(self, travel_method):
        self.travel_method = travel_method

    def move_to_next_cell(self):
        """移动到路径的下一个单元格 (或朝 dest 移动)"""
        if self.path:
            self.location = self.path.pop(0)  # 移除当前单元格


class Player(BaseObject):
    def __init__(self, resources, building_configs, purchase_configs):  # 增加 purchase_configs
        super().__init__()
        self.type = ObjectType.PLAYER
        self.resources: Dict[Resource, float] = {resource: 0.0 for resource in resources}
        self.manpower_allocation = {}
        self.avaliable_manpower = 0
        self.fleet = Fleet()
        self.avaliable_building_config = building_configs
        self.available_purchases = purchase_configs  # 存储可购买项
        self.characters = [{"name": "角色 1", "location": None}]
        self.explored_planets: List[str] = []
        self.action_points = 5
        self.max_action_points = 20
        self.action_points_recovery_per_minute = 0.1
        self.gold = 1000  # 初始金币

    def add_resource(self, resource_id: str, amount: float):
        """增加资源 (现在直接修改)"""
        for resource in self.resources:
            if resource == resource_id:
                self.resources[resource] += amount
                break

    def calculate_available_manpower(self):
        total_population = self.resources.get("resource.population", 0)
        allocated_manpower = 0
        for world_allocations in self.manpower_allocation.values():
            for building_id, manpower in world_allocations.items():
                allocated_manpower += manpower
        self.available_manpower = int(total_population - allocated_manpower)

    def tick(self, game):
        """
        普通 Player 的 tick 方法，暂时返回 None。
        未来可以通过用户输入或其他方式获取操作数据。
        """
        return None
