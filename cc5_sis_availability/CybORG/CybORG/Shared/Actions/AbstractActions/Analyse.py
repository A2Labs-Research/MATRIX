from random import choice
import pickle
import ast
import requests
from CybORG.Shared import Observation
from .Monitor import Monitor
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.AbstractActions import Monitor
from CybORG.Shared.Actions.ConcreteActions.DensityScout import DensityScout
from CybORG.Shared.Actions.ConcreteActions.SigCheck import SigCheck


class Analyse(Action):
    def __init__(self, session: int, agent: str, hostname: str):
        super().__init__()
        self.agent = agent
        self.session = session
        self.hostname = hostname

    def sim_execute(self, state) -> Observation:
        artefacts = [DensityScout, SigCheck]
        # find relevant session on the chosen host
        obs = Observation(True)
        sessions = [s for s in state.sessions[self.agent].values() if s.host == self.hostname]
        for process in state.hosts[self.hostname].processes:
            if process.name in ['WebFrontService', 'AuthService', 'DBService']:
                for connection in process.connections:
                    if "remote_address" in connection:
                        obs.add_process(hostid=self.hostname, process_name=process.name, status=process.status, 
                                        local_address=connection['local_address'], local_port=connection['local_port'], remote_address=connection['remote_address'], remote_port=connection['remote_port'])
            
        if len(sessions) > 0:
            session = choice(sessions)
            # run the artifacts on the chosen host
            for artifact in artefacts:
                sub_action = artifact(agent=self.agent, session=self.session, target_session=session.ident)
                sub_obs = sub_action.sim_execute(state)
                obs.combine_obs(sub_obs)
        # else:
        #     return Observation(False)

        return obs

    def __str__(self):
        return f"{self.__class__.__name__} {self.hostname}"
    
