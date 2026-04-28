from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from CybORG.Shared import Results
from CybORG.Shared.Actions import Monitor, Remove, Restore, Block
from collections import OrderedDict

class BlueReactRemoveAgent(BaseAgent):
    def __init__(self):
        self.host_list = []
        self.last_action = None
        self.initial_host = None

    def train(self, results: Results):
        pass

    def set_initial_host(self, initial_host:str):
        self.initial_host = initial_host

    def get_action(self, observation, action_space, true_obs = None):
        # add suspicious hosts to the hostlist if monitor found something
        # added line to allow for automatic monitoring.
        if self.last_action is not None and self.last_action == 'Monitor':
            for host_name, host_info in [(value['System info']['Hostname'], value) for key, value in observation.items() if key not in ['success', 'Network Activity']]:
                if host_name not in self.host_list and host_name != self.initial_host and 'Processes' in host_info and len([i for i in host_info['Processes'] if 'PID' in i]) > 0:
                    self.host_list.append(host_name)
        # assume a single session in the action space
        session = list(action_space['session'].keys())[0]
        if len(self.host_list) == 0:
            self.last_action = 'Monitor'
            return Monitor(agent='Blue', session=session)
        else:
            self.last_action = 'Remove'
            return Remove(hostname=self.host_list.pop(0), agent='Blue', session=session)

    def end_episode(self):
        self.host_list = []
        self.last_action = None
        self.initial_host = None

    def set_initial_values(self, action_space, observation):
        pass


class BlueReactRestoreAgent(BaseAgent):
    def __init__(self):
        self.host_list = []
        self.last_action = None
        self.initial_host = None

    def train(self, results: Results):
        pass

    def set_initial_host(self, initial_host:str):
        self.initial_host = initial_host

    def get_action(self, observation, action_space, true_obs = None):
        # add suspicious hosts to the hostlist if monitor found something
        # added line to reflect changes in blue actions
        if self.last_action is not None and self.last_action == 'Monitor':
            for host_name, host_info in [(value['System info']['Hostname'], value) for key, value in observation.items() if key not in ['success', 'Network Activity']]:
                if host_name not in self.host_list and host_name != self.initial_host and 'Processes' in host_info and len([i for i in host_info['Processes'] if 'PID' in i]) > 0:
                    self.host_list.append(host_name)
        # assume a single session in the action space
        session = list(action_space['session'].keys())[0]
        if len(self.host_list) == 0:
            self.last_action = 'Monitor'
            return Monitor(agent='Blue', session=session)
        else:
            self.last_action = 'Restore'
            return Restore(hostname=self.host_list.pop(0), agent='Blue', session=session)

    def end_episode(self):
        self.host_list = []
        self.last_action = None
        self.initial_host = None

    def set_initial_values(self, action_space, observation):
        pass


class BlueReactBlockAgent(BaseAgent):
    def __init__(self):
        self.host_dict = OrderedDict()
        self.last_action = None
        self.initial_host = None

    def train(self, results: Results):
        pass

    def set_initial_host(self, initial_host:str):
        self.initial_host = initial_host

    def get_action(self, observation, action_space, true_obs = None):
        # add suspicious hosts to the host dict if monitor found something
        if self.last_action is not None and self.last_action == 'Monitor':
            for host_name, host_info in [(value['System info']['Hostname'], value) for key, value in observation.items() if key not in ['success', 'Network Activity']]:
                # Case: Block raised an alert
                if 'Network Activity' in observation.keys():
                    if host_name != self.initial_host:
                        self.host_dict.pop(host_name, None)
                        self.host_dict[host_name] = "Block"
                # Case: Exploit or PrivilegeEscalate got noticed from Blue agent
                else:
                    if host_name not in self.host_dict.keys() and host_name != self.initial_host and 'Processes' in host_info and len([i for i in host_info['Processes'] if 'PID' in i]) > 0:
                        self.host_dict[host_name] = "Remove"

        # assume a single session in the action space
        session = list(action_space['session'].keys())[0]
        if len(self.host_dict) == 0:
            self.last_action = 'Monitor'
            return Monitor(agent='Blue', session=session)
        else:
            last_host, last_action = self.host_dict.popitem(last=False)
            self.last_action = last_action
            if self.last_action == 'Remove':
                return Remove(hostname=last_host, agent='Blue', session=session)
            else:
                return Block(hostname=last_host, agent='Blue', session=session)

    def end_episode(self):
        self.host_dict = OrderedDict()
        self.last_action = None
        self.initial_host = None

    def set_initial_values(self, action_space, observation):
        pass