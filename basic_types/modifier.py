from .enums import *

class ModifierConfig:
    def __init__(self, target_type, data_type, modifier_type, quantity, duration, delay):
        self.target_type : Target = target_type
        self.data_type : str = data_type
        self.modifier_type : ModifierType = modifier_type 
        self.quantity = quantity
        self.duration = duration
        self.delay = delay

class ModifierInstance:
    def __init__(self, target_id, config):
        self.target_id = target_id
        self.config = config
        self.life = 0