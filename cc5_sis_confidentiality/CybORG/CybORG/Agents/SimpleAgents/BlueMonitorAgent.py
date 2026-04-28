from CybORG.Shared.Actions import Monitor
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from typing import Any

class BlueMonitorAgent(BaseAgent):
    def __init__(self):
        pass

    def get_action(self,observation,action_space, true_obs = None):
        session = 0
        return Monitor(session=session,agent='Blue')


    def train(self, results):
        pass

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

    def __call__(self, *args: Any, **kwds: Any) -> Any:
            return self