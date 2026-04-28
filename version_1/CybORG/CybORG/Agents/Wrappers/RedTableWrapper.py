import math
from copy import deepcopy
from prettytable import PrettyTable
import numpy as np
from pprint import pprint

from CybORG.Agents.Wrappers.BaseWrapper import BaseWrapper
from CybORG.Agents.Wrappers.TrueTableWrapper import TrueTableWrapper
from CybORG.Shared.Actions.ConcreteActions.ExploitAction import ExploitAction


class RedTableWrapper(BaseWrapper):
    def __init__(self, env=None, agent=None, output_mode='table'):
        super().__init__(env,agent)
        self.env = TrueTableWrapper(env=env, agent=agent)
        self.agent = agent

        self.red_info = {}
        self.known_subnets = set()
        self.step_counter = -1
        self.id_tracker = -1
        self.output_mode = output_mode
        self.success = None

    def reset(self, agent=None):
        self.red_info = {}
        self.known_subnets = set()
        self.step_counter = -1
        self.id_tracker = -1
        self.success = None
        result = self.env.reset(agent)
        if agent =='Red':
            obs = self.observation_change(result.observation)
            result.observation = obs
        return result

    def get_table(self,output_mode='red_table'):
        if output_mode == 'red_table':
            return self._create_red_table()
        elif output_mode == 'true_table':
            return self.env.get_table()

    def observation_change(self, observation):
        self.success = observation['success']

        self.step_counter += 1
        if self.step_counter <= 0:
            self._process_initial_obs(observation)
        elif self.success:
            self._update_red_info(observation)

        if self.output_mode == 'table':
            obs = self._create_red_table()
        elif self.output_mode == 'vector':
            obs = self._create_vector()
        elif self.output_mode == 'raw':
            obs = observation
        else:
            raise NotImplementedError('Invalid output_mode')

        return obs

    def _process_initial_obs(self, obs):
        for hostid in obs:
            if hostid == 'success':
                continue
            host = obs[hostid]
            interface = host['Interface'][0]
            subnet = interface['Subnet']
            self.known_subnets.add(subnet)
            ip = str(interface['IP Address'])
            hostname = host['System info']['Hostname']
            self.red_info[ip] = [str(subnet), str(ip), hostname, False, 'Privileged']

    def _update_red_info(self, obs):
        action = self.get_last_action(agent='Red')
        name = action.__class__.__name__
        if name == 'DiscoverRemoteSystems':
            self._add_ips(obs)
        elif name == 'DiscoverNetworkServices':
            # ip = str(obs.popitem()[1]['Interface'][0]['IP Address'])
            # self.red_info[ip][3] = True

            item = obs.popitem()[1]
            if isinstance(item, dict):
                interface = item.get('Interface', [])
                ip = str(interface[0]['IP Address']) if interface and isinstance(interface, list) else None
                # print("IP is ", ip)
                if ip is not None:
                    self.red_info[ip][3] = True
                    
        elif name == 'ExploitRemoteService' or isinstance(action, ExploitAction):
            self._process_exploit(obs)
        elif name == 'PrivilegeEscalate':
            hostname = action.hostname
            self._process_priv_esc(obs, hostname)

    def _generate_name(self, datatype: str):
        self.id_tracker += 1
        unique_id = 'UNKNOWN_' + datatype + ': ' + str(self.id_tracker)
        return unique_id

    def _add_ips(self, obs):
        for hostid in obs:
            if hostid == 'success':
                continue
            host = obs[hostid]
            for interface in host['Interface']:
                ip = interface['IP Address']
                subnet = interface['Subnet']
                if subnet not in self.known_subnets:
                    self.known_subnets.add(subnet)
                if str(ip) not in self.red_info:
                    subnet = self._get_subnet(ip)
                    hostname = self._generate_name('HOST')
                    self.red_info[str(ip)] = [subnet, str(ip), hostname, False, 'None']
                elif self.red_info[str(ip)][0].startswith('UNKNOWN_'):
                    self.red_info[str(ip)][0] = self._get_subnet(ip)

    def _get_subnet(self, ip):
        for subnet in self.known_subnets:
            if ip in subnet:
                return str(subnet)
        return self._generate_name('SUBNET')

    def _process_exploit(self, obs):
        for hostid in obs:
            if hostid == 'success':
                continue

            host = obs[hostid]
            if 'Sessions' in host:
                ip = str(host['Interface'][0]['IP Address'])
                hostname = host['System info']['Hostname']
                session = host['Sessions'][0]
                access = 'Privileged' if 'Username' in session and session['Username'] in ['root', 'SYSTEM'] else 'User'

                self.red_info[ip][2] = hostname
                self.red_info[ip][4] = access

    def _process_priv_esc(self, obs, hostname):
        if obs['success'] == False:
            red_info = [info for info in self.red_info.values() if info[2] == hostname]
            if len(red_info) > 0:
                red_info[0][4] = 'None'
        else:
            for hostid in obs:
                if hostid == 'success':
                    continue
                host = obs[hostid]
                ip = host['Interface'][0]['IP Address']
    
                if 'Sessions' in host:
                    access = 'Privileged'
                    self.red_info[str(ip)][4] = access
                else:
                    subnet = self._get_subnet(ip)
                    hostname = self._generate_name('HOST')
    
                    if str(ip) not in self.red_info:
                        self.red_info[str(ip)] = [subnet, str(ip), hostname, False, 'None']
                    else:
                        self.red_info[str(ip)][0] = subnet
                        self.red_info[str(ip)][2] = hostname

    def _create_red_table(self):
        # The table data is all stored inside the ip nodes
        # which form the rows of the table
        table = PrettyTable([
            'Subnet',
            'IP Address',
            'Hostname',
            'Scanned',
            'Access',
        ])
        for ip in self.red_info:
            table.add_row(self.red_info[ip])

        table.sortby = 'IP Address'
        table.success = self.success
        return table

    def _create_vector(self, num_hosts=13):
        table = self._create_red_table()._rows

        # Get TrueTable to match IPs with Subnets and Hostnames
        true_table = self.get_table(output_mode='true_table').rows
        sort_hosts = ['User0', 'User1', 'User2', 'User3', 'User4', 'Enterprise0', 'Enterprise1', 'Enterprise2', 'Defender', 'Op_Server0', 'Op_Host0', 'Op_Host1', 'Op_Host2']
        true_table = [y for x in sort_hosts for y in true_table if y[2] == x]

        success_value = int(self.success.value) if self.success.value < 2 else -1
        proto_vector = [success_value]
        
        for row in true_table:
            position = [i for i, t in enumerate(table) if row[1] in t]
            host_obs = []
            if position != []:
                # Scanned
                scanned = int(table[position[0]][3])
                host_obs.append(scanned)

                # Access
                access = table[position[0]][4]
                if access == 'None':
                    value = [0, 0]
                elif access == 'User':
                    value = [1, 0]
                elif access == 'Privileged':
                    value = [0, 1]
                else:
                    raise ValueError('Table had invalid Access Level')
                host_obs.extend(value)
            else:
                host_obs = [-1, -1, -1]

            proto_vector.extend(host_obs)
        return np.array(proto_vector)

    def get_attr(self,attribute:str):
        return self.env.get_attr(attribute)

    def get_observation(self, agent: str):
        if agent != 'Red' or self.output_mode == 'raw':
            obs = self.get_attr('get_observation')(agent)
        elif self.output_mode == 'table':
            obs = self.get_table()
        elif self.output_mode == 'vector':
            obs = self._create_vector()
        else:
            raise NotImplementedError('Invalid output_mode')

        return obs

    def get_agent_state(self,agent:str):
        return self.get_attr('get_agent_state')(agent)

    def get_action_space(self,agent):
        return self.get_attr('get_action_space')(agent)

    def get_last_action(self,agent):
        return self.get_attr('get_last_action')(agent)

    def get_ip_map(self):
        return self.get_attr('get_ip_map')()

    def get_rewards(self):
        return self.get_attr('get_rewards')()
