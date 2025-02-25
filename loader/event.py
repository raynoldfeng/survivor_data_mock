class EventConfig:
    class Option:
        def __init__(self):
            self.judgment = None
            self.modifier_succ = None
            self.modifier_fail = None
    
    def __init__(self):
        self.type = None
        self.name = None
        self.cond = None
        self.occur = None
        self.init_text = None
        self.options = None
        self.judgment = None
        self.end_text = None
