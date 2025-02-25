from .imports import *
from .enums import *

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

def load_resources_from_csv(file_path: str) -> Dict[str, Resource]:
    resources = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                resource_id = row["id"]
                resource = Resource.from_csv_row(row)
                resources[resource_id] = resource
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
    except Exception as e:
        print(f"Error loading resources from CSV: {e}")
    return resources