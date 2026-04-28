import random
from pprint import pprint
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from CybORG.Shared import Results
from CybORG.Shared.Actions import PrivilegeEscalate, ExploitRemoteService, DiscoverRemoteSystems, Impact, DiscoverNetworkServices


class RedMeanderAgent_SIS_random(BaseAgent):
    # a red agent that meanders through scenario 1b
    def __init__(self):
        self.scanned_subnets = []
        self.scanned_ips = []
        self.exploited_ips = []
        self.escalated_hosts = []
        self.host_ip_map = {}
        self.last_host = None
        self.last_ip = None
        self.initial_host = None
    

    def train(self, results: Results):
        """allows an agent to learn a policy"""
        pass

    def get_action(self, observation, action_space, true_obs = None):
        """gets an action from the agent that should be performed based on the agent's internal state and provided observation and action space"""
        if self.initial_host is None:
            self.initial_host = [init for init in list(observation.keys()) if init != 'success'][0]

        self._process_success(observation)
        session = list(action_space['session'].keys())[0]
        
        # Always impact if able
        for host in self.escalated_hosts:
            if 'Auth' in host or 'Database' in host or 'Front' in host:
                self.last_host = host
                return Impact(agent='Red', hostname=host, session=session)
            
        # DiscoverRemoteSystems
        for subnet in action_space["subnet"]:
            if not action_space["subnet"][subnet] or subnet in self.scanned_subnets:
                continue
            self.scanned_subnets.append(subnet)
            return DiscoverRemoteSystems(subnet=subnet, agent='Red', session=session)
        
        # DiscoverNetworkServices
        addresses = [i for i in action_space["ip_address"] if 'not_exist' not in str(i)]
        random.shuffle(addresses)
        for address in addresses:
            if not action_space["ip_address"][address] or address in self.scanned_ips:
                continue
            self.scanned_ips.append(address)
            return DiscoverNetworkServices(ip_address=address, agent='Red', session=session)
        
        # PrivilegeEscalate
        hostnames = [x for x in action_space['hostname'].keys() if 'not_exist' not in x]
        random.shuffle(hostnames)
        for hostname in hostnames:
            # test if host is not known
            if not action_space["hostname"][hostname]:
                continue
            # test if host is already priv esc
            if hostname in self.escalated_hosts:
                continue
            # test if host is exploited
            if hostname in self.host_ip_map and self.host_ip_map[hostname] not in self.exploited_ips:
                continue
            self.escalated_hosts.append(hostname)
            self.last_host = hostname
            return PrivilegeEscalate(hostname=hostname, agent='Red', session=session)

        # ExploitRemoteService
        for address in addresses:
            # test if output of observation matches expected output
            if not action_space["ip_address"][address] or address in self.exploited_ips:
                continue
            self.exploited_ips.append(address)
            self.last_ip = address
            return ExploitRemoteService(ip_address=address, agent='Red', session=session)

        raise NotImplementedError('Red Meander has run out of options!')


    def _process_success(self, observation):
        if self.last_ip is not None:
            if observation['success'] == True:
                self.host_ip_map[[value['System info']['Hostname'] for key, value in observation.items()
                                  if key != 'success' and 'System info' in value
                                  and 'Hostname' in value['System info']][0]] = self.last_ip
            else:
                self._process_failed_ip()
            self.last_ip = None
        if self.last_host is not None:
            if observation['success'] == False:
                if self.last_host in self.escalated_hosts:
                    self.escalated_hosts.remove(self.last_host)
                if self.last_host in self.host_ip_map and self.host_ip_map[self.last_host] in self.exploited_ips:
                    self.exploited_ips.remove(self.host_ip_map[self.last_host])
            self.last_host = None

    def _process_failed_ip(self):
        self.exploited_ips.remove(self.last_ip)
        hosts_of_type = lambda y: [x for x in self.escalated_hosts if y in x]
        if len(hosts_of_type('Op')) > 0:
            for host in hosts_of_type('Op'):
                self.escalated_hosts.remove(host)
                ip = self.host_ip_map[host]
                self.exploited_ips.remove(ip)
        elif len(hosts_of_type('Defender')) > 0:
            for host in hosts_of_type('Defender'):
                self.escalated_hosts.remove(host)
                ip = self.host_ip_map[host]
                self.exploited_ips.remove(ip)

    def end_episode(self):
        self.scanned_subnets = []
        self.scanned_ips = []
        self.exploited_ips = []
        self.escalated_hosts = []
        self.host_ip_map = {}
        self.last_host = None
        self.last_ip = None
        self.initial_host = None

    def set_initial_values(self, action_space, observation):
        pass
