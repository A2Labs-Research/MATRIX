from random import choice

from CybORG.Shared import Observation
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.ConcreteActions.DefaceAction import DefaceAction
from CybORG.Simulator.State import State


class Impact(Action):
    def __init__(self, session: int, agent: str, hostname: str):
        super().__init__()
        self.agent = agent
        self.session = session
        self.hostname = hostname

    def sim_execute(self, state: State) -> Observation:
        # find session on the chosen host
        obs = Observation(success=False)
        sessions = [s for s in state.sessions[self.agent].values() if s.host == self.hostname]
        if len(sessions) == 0:
            # no valid session could be found on chosen host
            return Observation(success=False)
        # find if any session are already SYSTEM or root
        min_level = 0
        session = None
        for s in sessions:
            # else find if session is Admin or sudo
            if (s.username == 'root' or s.username == 'SYSTEM') and s.can_impact_servicename:
                session = s.ident
                obs = Observation(success=True)
                obs.add_session_info(hostid=self.hostname, **s.get_state())
                break
        # else use random session
        if session is None:
            session = choice(sessions).ident

        service_names = state.hosts[self.hostname].services.keys()
        for service_name in service_names:
            if service_name == state.sessions[self.agent][session].can_impact_servicename:
                if state.sessions[self.agent][session].username in ['root', 'SYSTEM']:
                    sub_action = DefaceAction(agent=self.agent, session=self.session, service=service_name, target_session=session)
                    obs = sub_action.sim_execute(state)
                break
            else:
                obs = Observation(success=False)

        return obs

    def __str__(self):
        return f"{self.__class__.__name__} {self.hostname}"
