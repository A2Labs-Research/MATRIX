import random
from pprint import pprint

from CybORG.Agents import BaseAgent
from CybORG.Shared import Results
from CybORG.Shared.Actions import PrivilegeEscalate, ExploitRemoteService, DiscoverRemoteSystems, Impact, DiscoverNetworkServices, Sleep


class B_lineAgent_SIS_random(BaseAgent):
    def __init__(self):
        self.action_index = -1
        self.action = None

        self.hosts = []
        self.scanned_hosts = []
        self.scanned_subnets = []
        self.last_ip_address = None
        self.last_subnet = None
        self.scanned_subnet = False
        self.initial_host = None

    def train(self, results: Results):
        """allows an agent to learn a policy"""
        pass


    def get_action(self, observation, action_space=None, true_obs=None):
        session = 0

        if observation['success'] == True or self.action_index == -1:
            self.action_index += 1

            if self.action_index == 0:
                self.initial_host = [init for init in list(observation.keys()) if init != 'success'][0]
                self.scanned_hosts.append(observation[self.initial_host]["Interface"][0]["IP Address"])
                self.last_subnet = observation[self.initial_host]["Interface"][0]["Subnet"]
                self.scanned_subnets.append(self.last_subnet)
                self.action = DiscoverRemoteSystems(session=session, agent="Red", subnet=self.last_subnet)

            if self.action_index == 1:
                for key, value in observation.items():
                    if key != "success":
                        if value["Interface"][0]["IP Address"] not in self.hosts:
                            self.hosts.append(value["Interface"][0]["IP Address"])
                interfaces = [ip for ip in self.hosts if (ip not in self.scanned_hosts and ip in self.last_subnet)]
                if interfaces != []:
                    self.last_ip_address = random.choice(interfaces)
                else:
                    self.last_ip_address = self.scanned_hosts[-1]
                self.scanned_hosts.append(self.last_ip_address)
                self.action = DiscoverNetworkServices(session=session, agent="Red", ip_address=self.last_ip_address)

            if self.action_index == 2:
                for key, value in observation.items():
                    if key != "success":
                        for p in value["Processes"]:
                            if p['Connections'][0]['local_port'] == 53:
                                self.scanned_hosts.append(value["Interface"][0]["IP Address"])
                                interfaces = [ip for ip in self.hosts if (ip not in self.scanned_hosts and ip in self.last_subnet)]
                                if interfaces != []:
                                    self.last_ip_address = random.choice(interfaces)
                                else:
                                    self.last_ip_address = self.scanned_hosts[-1]

                                self.scanned_hosts.append(self.last_ip_address)
                                self.action = DiscoverNetworkServices(session=session, agent="Red", ip_address=self.last_ip_address)
                                self.action_index = 1
                                return self.action
                self.action = ExploitRemoteService(session=session, agent="Red", ip_address=self.last_ip_address)

            if self.action_index == 3:
                self.hostname = [value for key, value in observation.items() if key != "success" and "System info" in value][0]["System info"]["Hostname"]
                self.action = PrivilegeEscalate(agent="Red", hostname=self.hostname, session=session)

            if self.action_index == 4:
                for key, value in observation.items():
                    if key != "success":          
                        if value["Interface"][0]["IP Address"] in self.hosts and len(observation.keys()) > 2:
                            continue
                        # if 'SIS' in key and ('Auth' in self.hostname or 'Database' in self.hostname):
                        if 'Auth' in self.hostname or 'Database' in self.hostname:
                            self.action = Impact(agent="Red", session=session, hostname=self.hostname)
                        elif value["Interface"][0]["IP Address"] not in self.hosts:
                            self.hosts.append(value["Interface"][0]["IP Address"])
                            self.last_ip_address = value["Interface"][0]["IP Address"]
                            self.scanned_hosts.append(self.last_ip_address)
                            self.action = DiscoverNetworkServices(session=session, agent="Red", ip_address=self.last_ip_address)
                            self.action_index = 1
                        elif value["Interface"][0]["Subnet"] not in self.scanned_subnets:
                            self.scanned_subnets.append(value["Interface"][0]["Subnet"])
                            self.last_subnet= value["Interface"][0]["Subnet"]
                            self.action = DiscoverRemoteSystems(session=session, agent="Red", subnet=self.last_subnet)
                            self.action_index = 0
                        else:
                            interfaces = [ip for ip in self.hosts if (ip not in self.scanned_hosts and ip in self.last_subnet)]
                            if interfaces != []:
                                self.last_ip_address = random.choice(interfaces)
                            else:
                                self.last_ip_address = self.scanned_hosts[-1]
                            self.scanned_hosts.append(self.last_ip_address)
                            self.action = DiscoverNetworkServices(session=session, agent="Red", ip_address=self.last_ip_address)
                            self.action_index = 1
            if self.action_index == 5:
                self.action = Impact(agent="Red", session=session, hostname=self.hostname)
                self.action_index = 4

        else:
            if 'ExploitRemoteService' in str(self.action):
                self.scanned_hosts.append(self.last_ip_address)
                interfaces = [ip for ip in self.hosts if (ip not in self.scanned_hosts and ip in self.last_subnet)]
                if interfaces != []:
                    self.last_ip_address = random.choice(interfaces)
                else:
                    self.last_ip_address = self.scanned_hosts[-1]

                self.scanned_hosts.append(self.last_ip_address)
                self.action = DiscoverNetworkServices(session=session, agent="Red", ip_address=self.last_ip_address)
                self.action_index = 1
                return self.action
            if 'PrivilegeEscalate' in str(self.action):
                self.action_index+=-1
                self.action = ExploitRemoteService(session=session, agent="Red", ip_address=self.last_ip_address)
            if 'Impact' in str(self.action):
                self.action_index+=-1
                self.action = PrivilegeEscalate(agent="Red", hostname=self.hostname, session=session)

            
        return self.action


    def end_episode(self):
        self.action_index = -1
        self.action = None

        self.hosts = []
        self.scanned_hosts = []
        self.scanned_subnets = []
        self.last_ip_address = None
        self.last_subnet = None
        self.scanned_subnet = False
        self.initial_host = None
        
    def set_initial_values(self, action_space, observation):
        pass
