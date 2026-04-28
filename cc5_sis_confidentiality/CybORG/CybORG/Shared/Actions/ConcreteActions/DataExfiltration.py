import random
from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Session import Session, RedAbstractSession
from CybORG.Simulator.State import State


class DataExfiltration(ConcreteAction):
    def __init__(self, agent: str, session: int, target_session: int, service: str):
        super().__init__(session, agent)
        self.service = service
        self.target_session = target_session
        self.prob_mapping = {
            'None': 0.0,
            'Low': 0.0,
            'Medium': 0.5,
            'High': 0.75,
        }
        self.detect_probs = {'_Database': 0.75, '_Auth': 0.5}

    def sim_execute(self, state: State):
        # check that both sessions exist
        if self.session not in state.sessions[self.agent] or self.target_session not in state.sessions[self.agent]:
            return Observation(False)

        # check that both sessions are active
        parent_session: RedAbstractSession = state.sessions[self.agent][self.session]
        client_session: Session = state.sessions[self.agent][self.target_session]
        if not parent_session.active or not client_session.active:
            return Observation(False)

        # get target host
        target_host: Host = state.hosts[client_session.host]

        # find chosen service on host
        if self.service not in target_host.services:
            return Observation(False)

        # action can be executed only if traffic isn't blocked
        if target_host.traffic_blocked:
            return Observation(False)

        availability = state.scenario.get_host(target_host.hostname).get('AvailabilityValue', 'Low')
        prob = self.prob_mapping[availability]
        random_exfiltration_prob = random.random()
        if random_exfiltration_prob > prob:
            # print(f'EXFILTRATION FAILED WITH PROBABILITY LOWER THAN {prob}')
            return Observation(False)
        # print(f'EXFILTRATION SUCCESS WITH PROBABILITY GREATER THAN {prob}')
        temp_proc = None
        tunnel_exists = None
        for proc in state.hosts[target_host.hostname].processes:
            if proc.name == 'tunnel':
                tunnel_exists = True
                temp_proc = proc
        if tunnel_exists:
            remote_ip_address = temp_proc.connections[0]['remote_address']
            if remote_ip_address not in target_host.blacklist_ips:
                state.exfiltrate_data(target_host.hostname)
                target_host.suspicious_network_activity = True
                for host_suffix, prob in self.detect_probs.items():
                    if target_host.hostname.endswith(host_suffix):
                        random_alert_prob = random.random()
                        if random_alert_prob > prob:
                            pass
                        else:
                            # print('BLUE RAISED AN ALERT WITH PROBABILITY', random_alert_prob)
                            target_host.events['SuspiciousActivity'].append(True)
                        break
        else:
            return Observation(False)
        return Observation(True)
