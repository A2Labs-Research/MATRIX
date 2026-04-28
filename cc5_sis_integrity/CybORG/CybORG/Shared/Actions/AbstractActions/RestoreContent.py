from random import choice

from CybORG.Shared import Observation
from .Monitor import Monitor
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.ConcreteActions.RestoreContentFromBackup import RestoreContentFromBackup
from CybORG.Simulator.Session import VelociraptorServer
from CybORG.Shared.Actions.AbstractActions import Monitor

class RestoreContent(Action):
    def __init__(self, session: int, agent: str, hostname: str):
        super().__init__()
        self.agent = agent
        self.session = session
        self.hostname = hostname

    def sim_execute(self, state) -> Observation:

        if self.session not in state.sessions[self.agent]:
            return Observation(False)
        sessions = [s for s in state.sessions[self.agent].values() if s.host == self.hostname]

        if len(sessions) > 0:
            session = choice(sessions)
            # restore host content
            obs = Observation(True)
            action = RestoreContentFromBackup(session=self.session, agent=self.agent, target_session=session.ident)
            obs = action.sim_execute(state)
            return obs
        else:
            return Observation(False)

    @property
    def cost(self):
        return -0.5

    def __str__(self):
        return f"{self.__class__.__name__} {self.hostname}"
