import math

class Vector3:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        # 用于 A* 算法的评估值
        self.f_score = float('inf')

    def distance(self, target):
        dx = target.x - self.x
        dy = target.y - self.y
        dz = target.z - self.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def __lt__(self, other):
        # 根据 f_score 进行比较
        return self.f_score < other.f_score
    
    def __str__(self):
        return f"（{self.x},{self.y},{self.z}）)"