# Copyright DST Group. Licensed under the MIT license.

from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.Enums import TrinaryEnum


class RewardCalculator:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.init_state = None
        self.init_obs = None
        self.previous_state = None
        self.previous_obs = None
        self.flat = False

        # Should this actually be a time.datetime?
        self.time = 0

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool) -> float:
        raise NotImplementedError

    def tick(self):
        self.time += 1

    def reset(self):
        self.previous_state = self.init_state
        self.previous_obs = self.init_obs
        self.time = 0


class EmptyRewardCalculator(RewardCalculator):
    def calculate_reward(self, current_state: dict, action: Action, agent_observations: dict, done: bool):
        return 0.

class SuccessRewardCalculator(RewardCalculator):
    def __init__(self, agent_name: str):
        super().__init__(agent_name=agent_name)
        self.reward = 0 

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool):
        self.reward = -10. if agent_observations[self.agent_name].success == TrinaryEnum.FALSE else 0.
        return self.reward