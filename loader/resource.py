from common import *
from basic_types.enums import *
from basic_types.resource import *

def load_resources_from_csv(file_path: str) -> Dict[str, Resource]:
    resources = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                id = row["id"]
                resource = Resource.from_csv_row(row)
                resources[id] = resource
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
    except Exception as e:
        print(f"Error loading resources from CSV: {e}")
    return resources