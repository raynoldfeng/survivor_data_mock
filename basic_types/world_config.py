class WorldConfig:
    def __init__(self, world_id, info, init_structures, explored_rewards):
        self.world_id = world_id
        self.info = info
        self.init_structures = init_structures
        self.explored_rewards = explored_rewards