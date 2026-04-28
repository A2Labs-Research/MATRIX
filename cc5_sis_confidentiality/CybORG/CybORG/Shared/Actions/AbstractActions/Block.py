from random import choice

from CybORG.Shared import Observation
from .Monitor import Monitor
from CybORG.Shared.Actions import Action
from CybORG.Simulator.Session import VelociraptorServer
from CybORG.Shared.Actions.AbstractActions import Monitor
from CybORG.Shared.Actions.ConcreteActions import BlockTraffic

class Block(Action):
    def __init__(self, session: int, agent: str, hostname: str):
        super().__init__()
        self.agent = agent
        self.session = session
        self.hostname = hostname

    def sim_execute(self, state) -> Observation:
        if self.session not in state.sessions[self.agent]:
            return Observation(False)
        
        # TODO: This should NOT be hard-coded.
        if 'Auth' not in self.hostname and 'Database' not in self.hostname:
            # print(f"Block action will not have any effect on {self.hostname}.")
            return Observation(False)

        parent_session: VelociraptorServer = state.sessions[self.agent][self.session]
        # find relevant session on the chosen host
        sessions = [s for s in state.sessions[self.agent].values() if s.host == self.hostname]

        
        if len(sessions) > 0:
            session = choice(sessions)
            obs = Observation(True)
            action = BlockTraffic(session=self.session, agent=self.agent, target_session=session.ident)
            action.sim_execute(state)
            return obs
        else:
            return Observation(False)

    @property
    def cost(self):
        return -0.5

    def __str__(self):
        return f"{self.__class__.__name__} {self.hostname}"
