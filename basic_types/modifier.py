from .enums import *

class ModifierConfig:
    def __init__(self, target_type, data_type, modifier_type, quantity, duration, delay):
        self.target_type : ObjectType = target_type
        self.data_type : str = data_type
        self.modifier_type : ModifierType = modifier_type 
        self.quantity = quantity
        self.duration = duration
        self.delay = delay
    
    def __str__(self):
        return f"ModifierConfig(\n" \
               f"  target_type={self.target_type},\n" \
               f"  data_type='{self.data_type}',\n" \
               f"  modifier_type={self.modifier_type},\n" \
               f"  quantity={self.quantity},\n" \
               f"  duration={self.duration},\n" \
               f"  delay={self.delay}\n" \
               f")"
    
class ModifierInstance:
    def __init__(self, target_id, config, request_id, owner_type, owner_id):
        self.target_id = target_id
        self.config = config
        self.life = 0
        self.request_id = request_id
        self.owner_type = owner_type
        self.owner_id = owner_id
