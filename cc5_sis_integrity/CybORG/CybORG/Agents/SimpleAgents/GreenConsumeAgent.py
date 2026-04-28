import random

from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from CybORG.Shared import Results
from CybORG.Shared.Actions import Sleep, GreenConsumeService

class GreenConsumeAgent(BaseAgent):
    def get_action(self,observation,action_space, true_obs = None):
        return GreenConsumeService(session=0, agent='Green')

    def train(self,results):
        pass

    def end_episode(self):
        pass

    def set_initial_values(self,action_space,observation):
        pass
