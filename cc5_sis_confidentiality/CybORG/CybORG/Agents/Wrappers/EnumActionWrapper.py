import copy
import inspect
from typing import Union, List
from rich import print
from CybORG.Shared.Actions.Action import InvalidAction
from CybORG.Agents.SimpleAgents import BaseAgent
from CybORG.Agents.Wrappers import BaseWrapper
from CybORG.Shared import Results, ActionSpace
from ipaddress import ip_address, ip_network
max_subnets = 4
max_hosts = 5


class EnumActionWrapper(BaseWrapper):
    def __init__(self, env: Union[type, BaseWrapper] = None, agent: BaseAgent = None, paddings=False):
        super().__init__(env, agent, paddings)
        self.possible_actions = None
        self.action_signature = {}
        self.paddings = paddings
        if agent == "Red":
            self.get_action_space("Red")
        else:
            self.get_action_space("Blue")
        self.sleep_action = None

    def find_max_target_session(self, possible_actions: list) -> int:
        """This function aims to find the max target session available in possible actions
        Args:
            possible_actions (list): all possible
        Returns:
            int: max target session available
        """
        # Assuming ActionSpace.MAX_SESSIONS is a predefined constant
        max_target_session_present: int = ActionSpace.MAX_SESSIONS
        for action in possible_actions:
            try:
                temp_target_session = action.target_session
                if temp_target_session > max_target_session_present:
                    max_target_session_present = temp_target_session
            except Exception as e:
                # Exception ignored, continue with next action
                pass
        return max_target_session_present

    def organize_actions_based_on_session(self, possible_actions: list, max_target_session_present: int) -> list:
        """This function aims to order the new possible actions without touching the initial ordering till 888 (for MAX_SESSIONS = 8)
        Args:
            possible_actions (list): list of all possible actions
            max_target_session_present (int): max targets session
        Returns:
            list: newly ordered list
        """
        if possible_actions is None:
            possible_actions = []
        old_action_list: list = []
        new_action_list: list = []

        if max_target_session_present == ActionSpace.MAX_SESSIONS - 1:
            self.possible_actions = possible_actions
        else:
            for action in possible_actions:
                try:
                    temp_target_session = action.target_session
                    if temp_target_session < ActionSpace.MAX_SESSIONS:
                        old_action_list.append(action)
                    else:
                        new_action_list.append(action)
                except Exception:
                    old_action_list.append(action)
            self.possible_actions = old_action_list
        return self.possible_actions

    def step(self, agent=None, action: int = None, flag: Union[bool, List[bool]] = None) -> Results:
        if action is not None:
            action = self.possible_actions[action]
            if isinstance(flag, bool):
                if flag is False:
                    action = InvalidAction(action)
            elif isinstance(flag, list):
                action = [InvalidAction for flags in flag if flags is False]
        return super().step(agent, action)

    def find_subnet_from_ip(self, ip, subnets):
        try:
            ip_obj = ip_address(ip)
            for subnet in subnets:
                subnet_obj = ip_network(subnet, strict=False)
                if ip_obj in subnet_obj:
                    return subnet
            return None
        except ValueError as e:
            print(f"Error: {e}")
            return None    

    def action_space_info(self, action_space):
        action_space_new = {}
        sub_count = 0
        subnets = list(action_space['subnet'].keys())
        for subnet in subnets:
            action_space_new['Subnet_' + str(sub_count)] = {}
            sub_count += 1

        # Create dict with Subnet and IP/Hostnames
        init = str(list(action_space['ip_address'].keys())[0])
        sub_count = 0
        for ip, hostname in zip(action_space['ip_address'].keys(), action_space['hostname'].keys()):
            current_ip_subnet = self.find_subnet_from_ip(ip, subnets)
            init_ip_subnet = self.find_subnet_from_ip(init, subnets)

            if current_ip_subnet == init_ip_subnet:
                action_space_new['Subnet_' + str(sub_count)][hostname] = ip
            else:
                # Append not_exist host in each subnet
                while len(action_space_new['Subnet_' + str(sub_count)]) < max_hosts:
                    action_space_new['Subnet_' + str(sub_count)]['Subnet_' + str(sub_count) + '_ZHost_' + str(len(action_space_new['Subnet_' + str(sub_count)])) + '_not_exist'] = False
                sub_count += 1
                action_space_new['Subnet_' + str(sub_count)][hostname] = ip
            init = ip
        while len(action_space_new['Subnet_' + str(sub_count)]) < max_hosts:
            action_space_new['Subnet_' + str(sub_count)]['Subnet_' + str(sub_count) + '_ZHost_' + str(len(action_space_new['Subnet_' + str(sub_count)])) + '_not_exist'] = False

        # Append not_exist subnets
        while len(action_space_new) < max_subnets:
            subnet_name = 'Subnet_' + str(len(action_space_new)) + '_not_exist'
            action_space_new[subnet_name] = {}
            for i in range(max_hosts):
                hostname = subnet_name + '_ZHost_' + str(i) + '_not_exist'
                action_space_new[subnet_name][hostname] = False
                
        return action_space_new

    def reorder_padding(self, action_space):
        to_move = {k: v for k, v in action_space.items() if any('Server' in x for x in v.keys())}
        remaining = {k: v for k, v in action_space.items() if not any('Server' in x for x in v.keys())}
        action_space = {**remaining, **to_move}

        for subnet, hosts in action_space.items():
            to_move = {k: v for k, v in hosts.items() if 'Server' in k}
            remaining = {k: v for k, v in hosts.items() if 'Server' not in k}
            results = {**remaining, **to_move}
            action_space[subnet] = results

        return action_space
    

    def action_space_modifications(self, action_space):
        
        action_space_ = copy.deepcopy(action_space)
        # Create custom action space to add paddings
        action_space_new = self.action_space_info(action_space_)
        # Reorder custom action space to reorder empty subnets and Defender/Server hosts
        action_space_new = self.reorder_padding(action_space_new)

        # Finalize action_space items to be replaced
        subnet_dict = action_space_['subnet']
        while len(list(action_space_new.keys())) > len(list(subnet_dict.keys())):
            items = list(subnet_dict.items())
            items.insert(-1, ('not_exist', False))
            subnet_dict = dict(items)
        hostnames_dict = {}
        ip_dict = {}
        count = 0
        for s, h in action_space_new.items():
            for hostname, ip in h.items():
                if ip == False:
                    hostnames_dict[hostname] = False
                    ip_dict['not_exist_' + str(count)] = False
                    count += 1
                else:
                    hostnames_dict[hostname] = True
                    ip_dict[ip] = True
                
        action_space_["ip_address"] = ip_dict
        action_space_["hostname"] = hostnames_dict
        action_space_["subnet"] = subnet_dict

        return action_space_

    def action_space_change(self, action_space: dict) -> int:

        # Keep action space stable by setting target_session = 1
        if list(action_space['agent'].keys())[0] == 'Red':
            action_space['target_session'] = {0: True}

        # if random, append not_exist elements
        if self.paddings:
            action_space = self.action_space_modifications(action_space=action_space)

        assert type(action_space) is dict, (
            f"Wrapper required a dictionary action space. " f"Please check that the wrappers below the ReduceActionSpaceWrapper return the action space as a dict "
        )
        possible_actions = []
        temp = {}
        params = ["action"]

        for i, action in enumerate(action_space["action"]):
            if action not in self.action_signature:
                self.action_signature[action] = inspect.signature(action).parameters
            param_list = [{}]

            for p in self.action_signature[action]:
                if p == "priority":
                    continue
                temp[p] = []
                if p not in params:
                    params.append(p)
                if len(action_space[p]) == 1:
                    for p_dict in param_list:
                        p_dict[p] = list(action_space[p].keys())[0]
                else:
                    new_param_list = []
                    for p_dict in param_list:
                        for key, val in action_space[p].items():
                            p_dict[p] = key
                            new_param_list.append({key: value for key, value in p_dict.items()})
                    param_list = new_param_list

            for p_dict in param_list:
                if str(action(**p_dict)) == "Sleep":
                    self.sleep_action = action(**p_dict)
                if self.paddings:
                    keys_to_check = ['hostname', 'subnet', 'ip_address']
                    if any(key in p_dict and "not_exist" in str(p_dict[key]) for key in keys_to_check):
                        possible_actions.append(self.sleep_action)
                    else:
                        possible_actions.append(action(**p_dict))
                else:
                    possible_actions.append(action(**p_dict))

        self.possible_actions = possible_actions
        max_target_session_present = self.find_max_target_session(possible_actions)
        self.possible_actions = self.organize_actions_based_on_session(possible_actions, max_target_session_present)

        return len(self.possible_actions)