from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.State import State
from CybORG.Simulator.File import File

import random 

class RestoreContentFromBackup(ConcreteAction):
    def __init__(self, session: int, agent: str, target_session: int):
        super(RestoreContentFromBackup, self).__init__(session, agent)
        self.target_session = target_session

    def sim_execute(self, state: State) -> Observation:
        obs = Observation()
        if self.session not in state.sessions[self.agent] or self.target_session not in state.sessions[self.agent]:
            obs.set_success(False)
            return obs
        target_host: Host = state.hosts[state.sessions[self.agent][self.target_session].host]

        if 'front' not in target_host.hostname.lower() and 'auth' not in target_host.hostname.lower():
            obs.set_success(False)
            return obs 

        target_host.files = []
        if target_host.original_files is not None:
            for file in target_host.original_files:
                target_host.files.append(File(**file.get_state()))


        obs.set_success(True)
        for agent, sessions in state.sessions.items():
            if agent == 'Red':
                for i in state.sessions['Red'].keys():
                    if state.sessions['Red'][i].host == target_host.hostname:    
                        if state.sessions['Red'][i].username == 'root':
                            state.sessions['Red'][i].username = 'ubuntu'
                        if state.sessions['Red'][i].username == 'SYSTEM':
                            state.sessions['Red'][i].username = 'vagrant'
        # input()
        uuid = state.game_uuid
        target_host.restore_content(uuid=uuid)

        return obs


