from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.State import State

class BlockTraffic(ConcreteAction):
    def __init__(self, session: int, agent: str, target_session: int):
        super(BlockTraffic, self).__init__(session, agent)
        self.session = session
        self.target_session = target_session

    def sim_execute(self, state: State) -> Observation:
        obs = Observation()
        if self.session not in state.sessions[self.agent] or self.target_session not in state.sessions[self.agent]:
            obs.set_success(False)
            return obs

        ####### Block in host level ######
        target_host: Host = state.hosts[state.sessions[self.agent][self.target_session].host]
        
        if 'DBService' in target_host.services.keys() or 'AuthService' in target_host.services.keys():
            if target_host.tunnel:
                for proc in target_host.processes:
                    if proc.name == 'tunnel':
                        tunnel_process = proc
                        break
                target_host.blacklist_ips.append(tunnel_process.connections[0]['remote_address'])
                target_host.block_traffic()
                target_host.tunnel_destroyed()
            obs.set_success(True)
            return obs
        else:
            obs.set_success(False)
            return obs
