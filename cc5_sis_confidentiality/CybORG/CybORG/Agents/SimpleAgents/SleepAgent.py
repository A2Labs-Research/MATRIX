# Copyright DST Group. Licensed under the MIT license.
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from CybORG.Shared.Actions import Sleep


class SleepAgent(BaseAgent):
    def __init__(self):
        self.initial_host = None

    def train(self, results):
        pass

    def get_action(self, observation, action_space, true_obs = None):
        return Sleep()

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass
