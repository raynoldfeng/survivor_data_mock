import math

class Vector3:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.f_score = float('inf')

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def distance(self, target):
        dx = target.x - self.x
        dy = target.y - self.y
        dz = target.z - self.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def __lt__(self, other):
        return self.f_score < other.f_score

    def __eq__(self, other):
        if other is not None:
            return (self.x, self.y, self.z) == (other.x, other.y, other.z)
        else:
            return False

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"

    # 加法运算符
    def __add__(self, other):
        if not isinstance(other, Vector3):
            raise TypeError("Unsupported operand type(s) for +: 'Vector3' and '{}'".format(type(other).__name__))
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    # 减法运算符
    def __sub__(self, other):
        if not isinstance(other, Vector3):
            raise TypeError("Unsupported operand type(s) for -: 'Vector3' and '{}'".format(type(other).__name__))
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    # 标量乘法
    def __mul__(self, scalar):
        if not isinstance(scalar, (int, float)):
            raise TypeError("Unsupported operand type(s) for *: 'Vector3' and '{}'".format(type(scalar).__name__))
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    # 标量除法
    def __truediv__(self, scalar):
        if not isinstance(scalar, (int, float)):
            raise TypeError("Unsupported operand type(s) for /: 'Vector3' and '{}'".format(type(scalar).__name__))
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)

    # 反向乘法（支持 2 * vector）
    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    # 反向除法（支持 10 / vector，虽然通常不需要）
    def __rtruediv__(self, scalar):
        return Vector3(scalar / self.x, scalar / self.y, scalar / self.z)

    # 向量点积
    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    # 向量叉积
    def cross(self, other):
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )