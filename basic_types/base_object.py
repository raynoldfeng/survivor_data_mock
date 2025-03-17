from basic_types.enums import *

class BaseObject:
    _object_id_counter = 0
    _objects = {}

    def __init__(self, *kwargs):
        self.object_id = BaseObject._object_id_counter
        self.object_type = ObjectType.SYSTEM
        BaseObject._object_id_counter += 1
        BaseObject._objects[self.object_id] = self

    @classmethod
    def get_object_by_id(cls, object_id):
        return cls._objects.get(object_id)