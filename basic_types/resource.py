from .enums import *
from common import *

class Resource:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.resources : List[ResourceConfig] = [] # type: ignore
            return cls._instance

    @classmethod
    def new_resource(cls, res):
        if not cls._instance:
            cls._instance = Resource()
        if res not in cls._instance.resources:
            cls._instance.resources.append(res)
    
    @classmethod
    def get_resource_by_id(cls, id:str):
        for res in cls._instance.resources:
            if res.id == id:
                return res
        return None

class ResourceConfig:
    def __init__(self):
        self.id: Optional[str] = None
        self.name_id: Optional[str] = None
        self.type: Optional[ResourceType] = None
        self.desc_id: Optional[str] = None
        self.acquire_id: Optional[str] = None

    def __str__(self):
        return f"ResourceConfig(\n" \
               f"  id={self.id},\n" \
               f"  name_id={self.name_id},\n" \
               f"  type={self.type},\n" \
               f"  desc_id={self.desc_id},\n" \
               f"  acquire_id={self.acquire_id}\n" \
               f")"
    
    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'ResourceConfig':
        resource = cls()
        resource.id = row["id"]
        resource.name_id = row["name"]
        resource.type = ResourceType(row["type"])
        resource.desc_id = row["desc"]
        resource.acquire_id = row["acquire"]
        Resource.new_resource(resource)
        return resource
