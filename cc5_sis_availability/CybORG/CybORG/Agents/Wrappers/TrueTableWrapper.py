from copy import deepcopy
from pprint import pprint
from prettytable import PrettyTable

from CybORG.Shared.Enums import TrinaryEnum
from CybORG.Agents.Wrappers.BaseWrapper import BaseWrapper

class TrueTableWrapper(BaseWrapper):
    def __init__(self,env=None,agent=None, observer_mode=True, paddings=False):
        super().__init__(env,agent)
        self.scanned_ips = set()
        self.step_counter = -1
        self.observer_mode = observer_mode
        self.paddings = paddings

    def reset(self, agent=None):        
        self.scanned_ips = set()  
        self.step_counter = -1
        result = self.env.reset(agent)        
        result.observation = self.observation_change(result.observation)        
        return result      

    def observation_change(self,observation):
        self.step_counter +=1
        self._update_scanned()

        return observation if self.observer_mode else self._create_true_table()

    def get_table(self):
        return self._create_true_table()

    def _update_scanned(self):
        if self.step_counter <= 0:
            return

        action = self.get_last_action(agent='Red')
        if action.__class__.__name__ == 'DiscoverNetworkServices':
            red_obs = self.get_observation(agent='Red')
            success = red_obs['success']
            if success:
                ip = next(iter(reversed(red_obs.items())))[0]
                self.scanned_ips.add(ip)

    def _create_true_table(self):
        true_obs = self.env.get_agent_state('True')
        table = PrettyTable([
            'Subnet',
            'IP Address',
            'Hostname',
            'Known',
            'Scanned',
            'Access',
            'Ports',
            ])

        for hostid in true_obs:
            if hostid == 'success':
                continue
            host = true_obs[hostid]
            for interface in host['Interface']:
                ip = interface['IP Address']
                ip_str = str(ip)
                if ip_str == '127.0.0.1':
                    continue
                if 'Subnet' not in interface:
                    continue
                subnet = interface['Subnet']
                hostname = host['System info']['Hostname']
                action_space = self.get_action_space(agent = 'Red')
                known = action_space['ip_address'][ip]
                scanned = True if ip_str in self.scanned_ips else False
                access = self._determine_red_access(host['Sessions'])
            ports = []
            for proc in host['Processes']:
                if 'Connections' in proc.keys():
                    for p in proc['Connections']:
                        if p['local_port'] not in ports:
                            ports.append(p['local_port'])
            table.add_row([subnet,ip_str,hostname,known,scanned,access,ports])

        table.sortby = 'Hostname'
        table.success = true_obs.get('success', False)
        return table

    def _determine_red_access(self,session_list):
        for session in session_list:
            if session['Agent'] != 'Red':
                continue
            privileged = session['Username'] in {'root','SYSTEM'}
            return 'Privileged' if privileged else 'User'

        return 'None'


    def get_attr(self,attribute:str):
        return self.env.get_attr(attribute)

    def get_observation(self, agent: str):
        return self.get_attr('get_observation')(agent)

    def get_agent_state(self,agent:str):
        if agent == 'True':
            output = self.get_table()
        else:
            output = self.get_attr('get_agent_state')(agent)

        return output

    def get_action_space(self,agent):
        return self.get_attr('get_action_space')(agent)

    def get_last_action(self,agent):
        return self.get_attr('get_last_action')(agent)

    def get_ip_map(self):
        return self.get_attr('get_ip_map')()

    def get_rewards(self):
        return self.get_attr('get_rewards')()

def true_obs_to_table(true_obs,env):
    print('Scanned column likely inaccurate.')
    wrapper = TrueTableWrapper(env,observer_mode=False)
    wrapper.step_counter = 1
    return wrapper.observation_change(true_obs)