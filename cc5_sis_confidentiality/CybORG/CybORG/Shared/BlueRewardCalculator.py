from collections import namedtuple

from CybORG.Shared import Scenario
from CybORG.Shared.RedRewardCalculator import DistruptRewardCalculator, PwnRewardCalculator
from CybORG.Shared.RewardCalculator import RewardCalculator, SuccessRewardCalculator
from CybORG.Shared.Enums import TrinaryEnum

HostReward = namedtuple('HostReward','confidentiality availability')

class RnDRewardCalculator(RewardCalculator):
    #rewarding successful remove actions and decoys that red agents tried to exploit
    def __init__(self, agent_name: str, scenario: Scenario):
        self.scenario = scenario
        self.decoy_list=[]
        super().__init__(agent_name)

    def reset(self):
        self.decoy_list=[]

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool) -> float:
        reward=0
        mylist_red=['ExploitRemoteService','BlueKeep','EternalBlue','FTPDirectoryTraversal','HarakaRCE','HTTPRFI','HTTPSRFI','SQLInjection','SSHBruteForce']
        mylist_blue=['DecoyApache','DecoyFemitter','DecoyFemitter','DecoyHarakaSMPT','DecoySmss','DecoySSHD','DecoySvchost','DecoyTomcat','DecoyVsftpd']
        
        if any(i in str(action['Blue']) for i in mylist_blue) and agent_observations['Blue'].data['success']:
            self.decoy_list.append(str(action['Blue']).split(' ')[1])
        if any(i in str(action['Red']) for i in mylist_red):
            hostip= str(action['Red']).split(' ')[1]
            if any(str(current_state[hostname]['Interface'][0]['IP Address']) == hostip for hostname in self.decoy_list):
                reward +=1

        if 'Remove' in str(action['Blue']) and agent_observations['Blue'].data['success'] == TrinaryEnum.TRUE:
            reward +=0.2
        else :
            reward += 0
        return reward


class ConfidentialityRewardCalculator(RewardCalculator):
    # Calculate punishment for defending agent based on compromise of hosts/data
    def __init__(self, agent_name: str, scenario: Scenario):
        self.scenario = scenario
        self.adversary = scenario.get_agent_info(agent_name).adversary
        super(ConfidentialityRewardCalculator, self).__init__(agent_name)
        self.infiltrate_rc = PwnRewardCalculator(self.adversary, scenario)
        self.compromised_hosts = {}

    def reset(self):
        self.infiltrate_rc.reset()

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool) -> float:
        self.compromised_hosts = {}
        reward = -self.infiltrate_rc.calculate_reward(current_state, action, agent_observations, done)
        self._calculate_compromised_hosts()
        return reward

    def _calculate_compromised_hosts(self):
        for host, value in self.infiltrate_rc.compromised_hosts.items():
            self.compromised_hosts[host] = -1 * value


class AvailabilityRewardCalculator(RewardCalculator):
    # Calculate punishment for defending agent based on reduction in availability
    def __init__(self, agent_name: str, scenario: Scenario):
        super(AvailabilityRewardCalculator, self).__init__(agent_name)
        self.adversary = scenario.get_agent_info(agent_name).adversary
        self.disrupt_rc = DistruptRewardCalculator(self.adversary, scenario)
        self.impacted_hosts = {}

    def reset(self):
        self.disrupt_rc.reset()

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool) -> float:
        self.impacted_hosts = {}
        reward = -self.disrupt_rc.calculate_reward(current_state, action, agent_observations, done)
        self._calculate_impacted_hosts()
        return reward

    def _calculate_impacted_hosts(self):
        for host, value in self.disrupt_rc.impacted_hosts.items():
            self.impacted_hosts[host] = -1 * value

class HybridAvailabilityConfidentialityRewardCalculator(RewardCalculator):
    # Hybrid of availability and confidentiality reward calculator
    def __init__(self, agent_name: str, scenario: Scenario):
        super(HybridAvailabilityConfidentialityRewardCalculator, self).__init__(agent_name)
        self.confidentiality_calculator = ConfidentialityRewardCalculator(agent_name, scenario)
        self.rnd_calculator = RnDRewardCalculator(agent_name, scenario)
        self.availability_calculator = AvailabilityRewardCalculator(agent_name, scenario)

    def reset(self):
        self.confidentiality_calculator.reset()
        self.rnd_calculator.reset()
        self.availability_calculator.reset()

    def calculate_reward(self, current_state: dict, action: dict, agent_observations: dict, done: bool) -> float:
        reward = self.confidentiality_calculator.calculate_reward(current_state, action, agent_observations, done)\
                 + self.rnd_calculator.calculate_reward(current_state, action, agent_observations, done)\
                 + self.availability_calculator.calculate_reward(current_state, action, agent_observations, done)

        self._compute_host_scores(current_state.keys())
        return reward

    def _compute_host_scores(self, hostnames):
        self.host_scores = {}
        compromised_hosts = self.confidentiality_calculator.compromised_hosts
        impacted_hosts = self.availability_calculator.impacted_hosts
        for host in hostnames:
            if host == 'success':
                continue
            compromised = compromised_hosts[host] if host in compromised_hosts else 0
            impacted = impacted_hosts[host] if host in impacted_hosts else 0
            reward_state = HostReward(compromised,impacted)  
                                    # confidentiality, availability
            self.host_scores[host] = reward_state
