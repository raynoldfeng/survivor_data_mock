import datetime

class BuildingInstance:
    def __init__(self, building_config, start_time=None):
        self.config = building_config
        self.start_time = start_time if start_time else datetime.datetime.now()
        self.is_constructing = True
        self.current_durability = 0

    @property
    def is_completed(self):
        elapsed_time = datetime.datetime.now() - self.start_time
        return elapsed_time.total_seconds() >= self.config.build_period

    def check_status(self):
        if self.is_constructing and self.is_completed:
            self.is_constructing = False
            self.current_durability = self.config.durability
        return self.is_constructing
