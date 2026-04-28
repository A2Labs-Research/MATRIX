from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.State import State
import random 

class RestoreFromBackup(ConcreteAction):
    def __init__(self, session: int, agent: str, target_session: int):
        super(RestoreFromBackup, self).__init__(session, agent)
        self.target_session = target_session

    def sim_execute(self, state: State) -> Observation:
        obs = Observation()
        if self.session not in state.sessions[self.agent] or self.target_session not in state.sessions[self.agent]:
            obs.set_success(False)
            return obs
        target_host: Host = state.hosts[state.sessions[self.agent][self.target_session].host]
        session = state.sessions[self.agent][self.session]
        target_session = state.sessions[self.agent][self.target_session]

        if not session.active or not target_session.active:
            obs.set_success(False)
            return obs

        old_sessions = {}
        for agent, sessions in target_host.sessions.items():
            old_sessions[agent] = {}
            for session in sessions:
                old_sessions[agent][session] = state.sessions[agent].pop(session)
        target_host.restore()

        if 'auth' in str(target_host).lower():
            proc_name = 'AuthService'
            remote_port = 9090
        elif 'database' in str(target_host).lower():
            proc_name = 'DBService'
            remote_port = 3306
        elif 'front' in str(target_host).lower():
            proc_name = 'WebFrontService'
        else:
            pass

        for host_name, v in state.hosts.items():
            if 'front' in host_name.lower():
                target_front_hostname = v
                target_front_ip = target_front_hostname.interfaces[1].ip_address
                proc_front_name = 'WebFrontService'

        if 'auth' in str(target_host).lower() or 'database' in str(target_host).lower():
            state.start_service(hostname=target_host, service_name=proc_name)
            target_ip = target_host.interfaces[1].ip_address
            roll_high_port = random.randint(10000, 50000)

            target_front_hostname.events['NetworkConnections'].append({'local_address': target_front_ip, 'local_port': roll_high_port, 
                                                                       'remote_address': target_ip, 'remote_port':remote_port})
            for proc in target_front_hostname.processes:
                if proc.name == proc_front_name:
                    proc.connections.append({'local_address': target_front_ip,'local_port': roll_high_port, 
                                             'remote_address': target_ip, 'remote_port':remote_port})

            target_host.events['NetworkConnections'].append({'local_address': target_ip, 'local_port': remote_port, 
                                                             'remote_address': target_front_ip, 'remote_port': roll_high_port})
            for proc in target_host.processes:
                if proc.name == proc_name:
                    proc.connections.append({'local_address': target_ip, 'local_port': remote_port, 
                                             'remote_address': target_front_ip, 'remote_port': roll_high_port})

        for agent, sessions in target_host.sessions.items():
            for session in sessions:
                state.sessions[agent][session] = old_sessions[agent][session]
        return obs
