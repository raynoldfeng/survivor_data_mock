from .enums import *
from common import *

class Resource:
    def __init__(self):
        self.name_id: Optional[str] = None
        self.type: Optional[ResourceType] = None
        self.desc_id: Optional[str] = None
        self.acquire_id: Optional[str] = None

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'Resource':
        resource = cls()
        resource.name_id = row["name"]
        resource.type = ResourceType(row["type"])
        resource.desc_id = row["desc"]
        resource.acquire_id = row["acquire"]
        return resource
