# loader/purchase_config.py
from common import *
from basic_types.enums import PurchaseType

class PurchaseConfig:
    def __init__(self, package_name, purchase_type, price):
        self.package_name = package_name
        self.purchase_type = purchase_type
        self.price = price
        self.content = {}  # {item_id: amount}

    def add_content(self, item_id, amount):
        self.content[item_id] = amount

    def __str__(self):
        return f"PurchaseConfig(package_name={self.package_name}, type={self.purchase_type}, price={self.price}, content={self.content})"

def load_purchase_configs(file_path: str) -> Dict[str, PurchaseConfig]:
    configs = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                package_name = row["package_name"]
                purchase_type = PurchaseType(row["type"])
                item_id = row["item_id"]
                amount = int(row["amount"])
                price = int(row["price"])

                if package_name not in configs:
                    configs[package_name] = PurchaseConfig(package_name, purchase_type, price)
                configs[package_name].add_content(item_id, amount)

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
    except Exception as e:
        print(f"Error loading purchase configs from CSV: {e}")
    return configs