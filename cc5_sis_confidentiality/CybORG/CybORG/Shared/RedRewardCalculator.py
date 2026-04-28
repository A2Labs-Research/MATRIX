# Copyright DST Group. Licensed under the MIT license.
from collections import namedtuple
from pprint import pprint
from CybORG.Shared import Scenario
from CybORG.Shared.Actions import FindFlag, Impact
from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.Enums import OperatingSystemType
from CybORG.Shared.RewardCalculator import RewardCalculator

WIN_REWARD = 0
LOSE_REWARD = 0
SESSION_REWARD = 0
ROOT_SESSION_REWARD = 0
LOSE_SESSION_REWARD = 0
LOSE_ROOT_SESSION_REWARD = 0

REWARD_MAX_DECIMAL_PLACES = 1
HostReward = namedtuple('HostReward','confidentiality availability')

class DiscoverRewardCalculator(RewardCalculator):
    # this reward calculator provides a reward to Red due to new information gained from the network
    def __init__(self, agent_name: str, scenario: Scenario):
        super().__init__(agent_name)
        self.old_total = 0
        self.scenario = scenario
        self.discovered_hosts = {}
        self.discovered_ips = {}

    def reset(self):
        self.old_total = 0

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool):

        for host, info in current_state.items():
            if host == 'success':
                continue

            if 'Sessions' in info:
                for session in info['Sessions']:
                    if session['Agent'] == self.agent_name:
                        # print('---', host)
                        # pprint(info)
                        if host in self.discovered_hosts.values():
                            pass
                        else:
                            self.discovered_hosts[str(info['Interface'][0]['IP Address'])] = host

        agent_observations['Red'].data
        for key, value in agent_observations['Red'].data.items():
            if key == 'success':
                continue
            if 'Subnet_' in key:
                self.discovered_ips[str(value['Interface'][0]['IP Address'])] = key
            elif key not in self.discovered_ips.keys():
                if key in self.discovered_hosts.keys():
                    self.discovered_ips[key] = self.discovered_hosts[key]
                else:
                    self.discovered_ips[key] = None
            else:
                if key in self.discovered_hosts.keys():
                    self.discovered_ips[key] = self.discovered_hosts[key]
                else:
                    pass

        # find the difference from the old privileged sessions
        total_ip = len(list(self.discovered_ips.keys())) * 0.1     # Reward only for discovered ips
        total_hostname = (len([k for k,v in self.discovered_ips.items() if v is not None]) * 0.1)     # Reward only for discovered hostnames
        total = total_ip    + total_hostname

        # print(self.discovered_hosts)
        # print(self.discovered_ips)
        # print(total, total_ip, total_hostname)
        reward = total
        self.old_total = total
        return round(reward, REWARD_MAX_DECIMAL_PLACES)


class PwnRewardCalculator(RewardCalculator):
    # this reward calculator provides a reward to Red due to changes in the number of privileged sessions
    def __init__(self, agent_name: str, scenario: Scenario):
        super().__init__(agent_name)
        self.old_total = 0
        self.scenario = scenario
        self.mapping = {'None': 0.0,
                        'Low': 0.1,
                        'Medium': 1.0,
                        'High': 10.0}

        self.compromised_hosts = {}

    def reset(self):
        self.old_total = 0

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool):
        root_sessions = 0
        system_sessions = 0
        self.compromised_hosts = {}
        for host, info in current_state.items():
            if host == 'success':
                continue

            if 'Sessions' in info:
                for session in info['Sessions']:
                    if session['Agent'] == self.agent_name:
                        # count the number of root sessions
                        if session['Username'] == 'root' and info['System info']['OSType'] == OperatingSystemType.LINUX:
                            confidentiality_value = self.mapping[self.scenario.get_host(host).get('ConfidentialityValue', 'Low')]

                            root_sessions += confidentiality_value
                            self.compromised_hosts[host] = confidentiality_value
                            break
                        # count the number of SYSTEM sessions
                        if session['Username'] == 'SYSTEM' and info['System info']['OSType'] == OperatingSystemType.WINDOWS:
                            confidentiality_value = self.mapping[self.scenario.get_host(host).get('ConfidentialityValue', 'Low')]
                            system_sessions += confidentiality_value
                            self.compromised_hosts[host] = confidentiality_value
                            break

        # find the difference from the old privileged sessions
        total = root_sessions + system_sessions
        reward = total #- self.old_total
        self.old_total = total
        return round(reward, REWARD_MAX_DECIMAL_PLACES)


class DistruptRewardCalculator(RewardCalculator):
    # calculates the reward for disrupting the network
    def __init__(self, agent_name: str, scenario: Scenario):
        super(DistruptRewardCalculator, self).__init__(agent_name)
        self.scenario = scenario
        self.mapping = {'None': 0.0,
                        'Low': 0.0,
                        'Medium': 5.0,
                        'High': 10.0}

        self.impacted_hosts = {}

    def reset(self):
        self.ots = None

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool):
        exfitrations = {}
        for host_info in current_state.values():
            if type(host_info) is not dict:
                continue
            if 'exfiltration_times' in host_info['System info'] and host_info['System info']['exfiltration_times'] > 0:
                exfitrations[host_info['System info']['Hostname']] = host_info['System info']['exfiltration_times']

        return sum([times * self.mapping[self.scenario.get_host(host).get('AvailabilityValue', 'Low')] for host, times in exfitrations.items()])
    
class HybridImpactPwnRewardCalculator(RewardCalculator):
    # Hybrid of availability and confidentiality reward calculator
    def __init__(self, agent_name: str, scenario: Scenario):
        super(HybridImpactPwnRewardCalculator, self).__init__(agent_name)
        self.pwn_calculator = PwnRewardCalculator(agent_name, scenario)
        self.disrupt_calculator = DistruptRewardCalculator(agent_name, scenario)
        self.host_scores = {}

    def reset(self):
        self.pwn_calculator.reset()
        self.disrupt_calculator.reset()

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool) -> float:
        pwn_reward = self.pwn_calculator.calculate_reward(current_state, action, agent_observations, done)
        distrupt_reward = self.disrupt_calculator.calculate_reward(current_state, action, agent_observations, done)
        reward = pwn_reward + distrupt_reward

        self._compute_host_scores(current_state.keys())
        return round(reward, REWARD_MAX_DECIMAL_PLACES)

    def _compute_host_scores(self, hostnames):
        self.host_scores = {}
        compromised_hosts = self.pwn_calculator.compromised_hosts
        impacted_hosts = self.disrupt_calculator.impacted_hosts
        for host in hostnames:
            if host == 'success':
                continue
            compromised = compromised_hosts[host] if host in compromised_hosts else 0
            impacted = impacted_hosts[host] if host in impacted_hosts else 0
            reward_state = HostReward(compromised,impacted)  
            self.host_scores[host] = reward_state

