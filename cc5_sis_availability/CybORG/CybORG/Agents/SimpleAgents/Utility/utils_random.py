# Utility functions to support extanded library of agents
from CybORG.Shared import ActionSpace
from copy import deepcopy
from prettytable import PrettyTable
import inspect
from CybORG.Shared.Actions import *
from CybORG.Agents.Wrappers import EnumActionWrapper2,RedTableWrapper,BlueTableWrapper
import numpy as np
import math
from pprint import pprint
from ipaddress import IPv4Network, IPv4Address
from CybORG.Shared.Actions.ConcreteActions.ExploitAction import ExploitAction
import copy
import yaml

max_subnets = 4
max_hosts = 5

#takes action from cage2 action space and returns the same action on cage5 action space
def translate_action(env, agent, action, to_cage5):
    new_action, old_action = None, None
    cage_5_enum_action_wrapper = EnumActionWrapper2(env=env, paddings=True)
    cage_5_action_space = cage_5_enum_action_wrapper.get_action_space(agent=agent)
    cage_5_action_space = {i: str(cage_5_action_space[i]) for i in range(len(cage_5_action_space))}
    #pprint(cage_5_action_space)

    cage2_enum_action_wrapper = EnumActionWrapper2(env=env, paddings=False)
    cage2_action_space = cage2_enum_action_wrapper.get_action_space(agent=agent)
    cage2_action_space = {i: str(cage2_action_space[i]) for i in range(len(cage2_action_space))}
    #pprint(cage2_action_space)

    if to_cage5:  # translate action from cage2 to cage5
        old_action = cage2_action_space[action]
        for k, v in cage_5_action_space.items():
            if v == old_action:
                new_action = k
                break
    else:  # translate action from cage5 to cage2
        old_action = cage_5_action_space[action]
        for k, v in cage2_action_space.items():
            if v == old_action:
                new_action = k
                break
    return new_action


def translate_observation(env, agent, observation, to_cage5,path):
    with open(path, "r") as file:
        data = yaml.safe_load(file)

    if agent=='Red':
        cage_5_table_wrapper = RedTableWrapper(env=env, paddings=True)
    else: 
        cage_5_table_wrapper = BlueTableWrapper(env=env, paddings=True)
    cage_5_sort_hosts = data["Subnets"]
    cage_5_sort_hosts = cage_5_table_wrapper.add_nonexistent_hosts(cage_5_sort_hosts)

    cage_2_sort_hosts = list(data["Hosts"].keys())

    observation=observation
    new_obs=[observation[0]]
    observation=observation[1:]
    if to_cage5:
        i=0
        for host in cage_5_sort_hosts:
            if host in cage_2_sort_hosts:
                new_obs.extend([observation[3*i],observation[3*i+1],observation[3*i+2]])
                i+=1
            else:
                new_obs.extend([-1,-1,-1])
    else:
        for i,host in enumerate(cage_5_sort_hosts):
            if host in cage_2_sort_hosts:
                new_obs.extend([observation[3*i],observation[3*i+1],observation[3*i+2]])
    return new_obs


class ActionMappingRandom:
    def __init__(self):
        self.action_signature = {}
        self.possible_actions = None
        self.action_space = None
        self.scanned_ips = set()

    def action_mapping_red(self, action_space, true_table):
        self.action_space = action_space
        list_of_actions = self.action_space_change(action_space)
        true_table_dict = self.prettytable_to_dict(true_table)
        pprint(true_table_dict)
        dict_to_return = {"status": "success"}
        for i in range(len(list_of_actions)):
            action_dict = self.identify_action(list_of_actions[i], true_table_dict, i)
            dict_to_return[i] = action_dict

        return dict_to_return

    def action_mapping(self, action_space, true_obs):
        self.action_space = action_space
        list_of_actions = self.action_space_change(action_space)
        true_table = self.get_agent_state(true_obs)
        true_table_dict = self.prettytable_to_dict(true_table)
        dict_to_return = {"status": "success"}
        for i in range(len(list_of_actions)):
            action_dict = self.identify_action(list_of_actions[i], true_table_dict, i)
            dict_to_return[i] = action_dict

        return dict_to_return

    def append_ips(self, ips_dict: dict, host_count: dict) -> dict:
        my_host_count = copy.deepcopy(host_count)
        added = 0  # how many have been added
        must_add = 0  # how many should be added
        for v in my_host_count.values():
            must_add += max_hosts - int(v)  # 5 hosts per subnet so 5 ips

        new_dict = {}
        # iteration of the list of keys 2 by 2. If one key is different form the other it means that we changed
        # subnet so we need to add not_exist_ips in between.
        key_iter = iter(ips_dict.keys())
        next_key = next(key_iter)
        subnet_modified = 0  # store which subnet we modify
        for k, v in ips_dict.items():
            new_dict[k] = v
            try:
                # Get the next key
                next_key = next(key_iter)
                if ".".join(str(k).split(".")[:-1]) != ".".join(str(next_key).split(".")[:-1]) and subnet_modified < max_subnets:  # first 9 values of the ip address is the subnet
                    for i in range(max_hosts - my_host_count[subnet_modified]):  # add until each subnet has 5 ips
                        new_dict[f"not_exist_{added}"] = False
                        added += 1
                    subnet_modified += 1
            except StopIteration:
                break
        # if more hosts should be added add them in the end. This happens if a whole subnet does not exist
        while added < must_add:
            new_dict[f"not_exist_{added}"] = False
            added += 1

        myKeys = list(new_dict.keys())
        new_chunk_list = [myKeys[x : x + max_hosts] for x in range(0, len(myKeys), max_hosts)]
        for chunk in range(len(new_chunk_list)):
            if all(["not_exist" in str(element) for element in new_chunk_list[chunk]]) and chunk != len(new_chunk_list):
                new_chunk_list[chunk], new_chunk_list[chunk - 1] = new_chunk_list[chunk - 1], new_chunk_list[chunk]
                break
        for item in reversed(new_chunk_list[-1]):
            if "not_exist" not in str(item):
                new_chunk_list[-1][new_chunk_list[-1].index(item)], new_chunk_list[-1][-1] = new_chunk_list[-1][-1], new_chunk_list[-1][new_chunk_list[-1].index(item)]
                break
        myKeys = [j for i in new_chunk_list for j in i]
        new_dict = {i: new_dict[i] for i in myKeys}

        return new_dict

    def action_space_modifications(self, action_space):
        action_space_ = copy.deepcopy(action_space)
        max_network_hosts = max_subnets * max_hosts
        host_count = {key: 0 for key in list(range(max_subnets))}
        for key, value in action_space_["hostname"].items():
            subnet_num = int(key.split("_")[1])
            host_count[subnet_num] += 1

        # append ips
        # missing_ips = max_network_hosts - len(action_space_["ip_address"])
        # for missing_ip in range(missing_ips):
        #     action_space_["ip_address"]["not_exist_" + str(missing_ip)] = False
        action_space_["ip_address"] = self.append_ips(action_space_["ip_address"], host_count)

        # append hostnames
        for k, v in host_count.items():
            new_num = v
            while new_num < max_hosts:
                action_space_["hostname"][f"Subnet_{k}_Host_{new_num}_not_exist"] = False
                new_num += 1
        myKeys = list(action_space_["hostname"].keys())
        myKeys.sort()
        new_chunk_list = [myKeys[x : x + max_hosts] for x in range(0, len(myKeys), max_hosts)]
        for chunk in range(len(new_chunk_list)):
            if any(["Op_Server" in element for element in new_chunk_list[chunk]]) and chunk != len(new_chunk_list):
                new_chunk_list[chunk], new_chunk_list[-1] = new_chunk_list[-1], new_chunk_list[chunk]
        myKeys = [j for i in new_chunk_list for j in i]
        action_space_["hostname"] = {i: action_space_["hostname"][i] for i in myKeys}

        # append subnets
        counter = 0
        while len(action_space_["subnet"]) < max_subnets:
            action_space_["subnet"][f"not_exist_{counter}"] = False
            counter += 1
        myKeys = list(action_space_["subnet"].keys())
        for key in myKeys:
            if "not_exist" in str(key):
                myKeys[myKeys.index(key) - 1], myKeys[-1] = myKeys[-1], myKeys[myKeys.index(key) - 1]
                break
        action_space_["subnet"] = {i: action_space_["subnet"][i] for i in myKeys}
        # print(50*'*')
        # print(action_space_["ip_address"])
        # print(action_space_["hostname"])
        # print(action_space_["subnet"])
        return action_space_

    def action_space_change(self, action_space: dict) -> list:

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
                if any("not_exist" in item for item in [str(v) for v in p_dict.values()]):
                    possible_actions.append(self.sleep_action)
                else:
                    possible_actions.append(action(**p_dict))

        self.possible_actions = possible_actions
        max_target_session_present = self.find_max_target_session(possible_actions)
        self.possible_actions = self.organize_actions_based_on_session(possible_actions, max_target_session_present)

        return self.possible_actions

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
            # for i in range(ActionSpace.MAX_SESSIONS, max_target_session_present + 1):
            #     for action in new_action_list:
            #         if action.target_session == i:
            #             old_action_list.append(action)
            self.possible_actions = old_action_list
        return self.possible_actions

    def get_agent_state(self, true_obs):
        output = self.get_table(true_obs)
        return output

    def get_table(self, true_obs):
        return self._create_true_table(true_obs)

    def _create_true_table(self, true_obs):
        # true_obs = deepcopy(self.env.get_agent_state('True'))
        success = true_obs.pop("success")

        table = PrettyTable(
            [
                "Subnet",
                "IP Address",
                "Hostname",
                "Known",
                "Scanned",
                "Access",
            ]
        )

        for hostid in true_obs:
            host = true_obs[hostid]
            for interface in host["Interface"]:
                ip = interface["IP Address"]
                if str(ip) == "127.0.0.1":
                    continue
                if "Subnet" not in interface:
                    continue
                subnet = interface["Subnet"]
                hostname = host["System info"]["Hostname"]
                #  action_space = self.get_action_space(agent = 'Red')
                known = self.action_space["ip_address"][ip]
                scanned = True if str(ip) in self.scanned_ips else False
                access = self._determine_red_access(host["Sessions"])

                table.add_row([subnet, str(ip), hostname, known, scanned, access])

        table.sortby = "Hostname"
        table.success = success
        return table

    def _determine_red_access(self, session_list):
        for session in session_list:
            if session["Agent"] != "Red":
                continue
            privileged = session["Username"] in {"root", "SYSTEM"}
            return "Privileged" if privileged else "User"

        return "None"

    def prettytable_to_dict(self, table):
        headers = table.field_names
        table_str = str(table)
        rows = table_str.split("\n")[2:-1]  # Split the table string by newlines and exclude the header and footer
        data = []
        for row in rows:
            row_data = {}
            cells = row.split("|")[1:-1]  # Split the row by pipes and exclude empty cells and separators
            for idx, header in enumerate(headers):
                if idx < len(cells):
                    row_data[header.strip()] = cells[idx].strip()  # Strip whitespace from cells and headers
                else:
                    row_data[header.strip()] = None
            data.append(row_data)
        return data[1:]

    def identify_action(self, action, table_dict, number):
        action_name = action.__class__.__name__
        hostname = ""
        ip_address = ""
        subnet = ""
        target_session = ""
        try:
            hostname = action.hostname
            ip_address, subnet = self.get_based_on_hostname(hostname, table_dict)
        except:
            pass
        if ip_address == "":
            try:
                ip_address = str(action.ip_address)
                hostname, subnet = self.get_based_on_ip_address(ip_address, table_dict)
            except:
                pass
        if subnet == "":
            try:
                subnet = str(action.subnet)
            except:
                pass
        if target_session == "":
            try:
                target_session = action.target_session
            except:
                pass
        dict_to_return = {"number": number, "name": action_name, "hostname": hostname, "ip_address": ip_address, "subnet": subnet, "target_session": target_session}
        return dict_to_return

    def get_based_on_hostname(self, hostname, table_dict):
        for dictionary in table_dict:
            if dictionary["Hostname"] == hostname:
                return str(dictionary["IP Address"]), str(dictionary["Subnet"])

    def get_based_on_ip_address(self, ip_address, table_dict):
        for dictionary in table_dict:
            if dictionary["IP Address"] == str(ip_address):
                return dictionary["Hostname"], str(dictionary["Subnet"])

    """ Test Valid Actions for Random Topology"""

    def test_valid_action_rt(self, action, obs, action_mapping):
        # Create host_mapping
        mapping_obs = {"success": obs[0]}
        sort_hosts = []

        subnet_num = 0
        not_exist_counter = 0
        for k, v in action_mapping.items():
            if k == "status":
                continue
            if v["name"] == "DiscoverNetworkServices" and v["hostname"] == "Subnet_0_Host_0":
                start_ = int(v["number"])
            if v["name"] == "DiscoverNetworkServices" and "Op_Server" in v["hostname"]:
                end_ = int(v["number"]) + 1
        for k, v in action_mapping.items():
            if k != "status" and k in range(start_, end_):
                if v["name"] == "DiscoverNetworkServices":
                    sort_hosts.append(v["hostname"])
                    subnet_num = int(v["hostname"][7])
                else:
                    sort_hosts.append(f"Subnet_{subnet_num}_Host_not_exist_{not_exist_counter}")
                    not_exist_counter += 1

        subnet_host_list = []
        subnet_dict = {}
        subnet_cidr = []
        for h in sort_hosts:
            subnet_ = h[7]
            while len(subnet_host_list) <= int(subnet_):
                subnet_host_list.append([])
            subnet_host_list[int(subnet_)].append(h)
            for index, d in enumerate(action_mapping):
                if index != 0 and index < len(action_mapping) - 1:
                    if action_mapping[index]["hostname"] == h and action_mapping[index]["name"] == "DiscoverNetworkServices":
                        subnet_index = index
                        break
            if action_mapping[subnet_index]["subnet"] not in subnet_cidr:
                subnet_cidr.append(action_mapping[subnet_index]["subnet"])
        subnet_dict = dict(zip(subnet_cidr, subnet_host_list))

        for i, host in zip(range(0, len(obs) - 1, 3), sort_hosts):
            mapping_obs[host] = [obs[i + j] for j in range(1, 3 + 1)]

        # Get info from action_mapping
        action_details = action_mapping[action]
        action_name = action_details["name"]
        subnet = action_details["subnet"]
        host_name = action_details["hostname"]

        # Rules for every action
        if action_name == "DiscoverRemoteSystems":
            for cidr, subnets_ in subnet_dict.items():
                if subnet == cidr:
                    if any(flag == 1 for flag in [mapping_obs[host][2] for host in subnets_]):
                        return True
        elif action_name == "DiscoverNetworkServices":
            if "Defender" in host_name:
                return False
            if mapping_obs[host_name][0] != -1:
                return True
        elif action_name == "ExploitRemoteService":
            if "Defender" in host_name:
                return False
            if mapping_obs[host_name][0] == 1:
                return True
        elif action_name == "PrivilegeEscalate":
            if "Defender" in host_name:
                return False
            if mapping_obs[host_name][0] == 1 and (mapping_obs[host_name][1] == 1 or mapping_obs[host_name][2] == 1):
                return True
        elif action_name == "Impact":
            if "Defender" in host_name:
                return False
            if mapping_obs[host_name][2] == 1:
                return True
        elif action_name == "InvalidAction":
            return False
        elif action_name == "Sleep":
            return False
        else:
            if "Defender" in host_name:
                return False
            # if mapping_obs[host_name][0] == 1 or (mapping_obs[host_name][1] + mapping_obs[host_name][2] > 0):
            if mapping_obs[host_name][0] == 1:
                return True
        return False

    """ New mask using the observation for random topologies """

    def mask_fn_new(self, obs, action_mapping) -> np.ndarray:
        mask = []
        for action in range(len(action_mapping) - 1):
            valid_act = self.test_valid_action_rt(action, obs, action_mapping)
            mask.append(valid_act)
            # if valid_act:
            #     print('---', action_mapping[action]['name'], action_mapping[action]['hostname'], action_mapping[action]['ip_address'], action_mapping[action]['subnet'], valid_act)
            # else:
            #     print(action_mapping[action]['name'], action_mapping[action]['hostname'], action_mapping[action]['ip_address'], action_mapping[action]['subnet'], valid_act)
        return mask


def numeric_to_cyborg_action(mapped_action):
    action = None
    hostname = mapped_action["hostname"]

    subnet = mapped_action["subnet"]
    if subnet:
        subnet = IPv4Network(subnet, strict=False)

    ip_address = mapped_action["ip_address"]
    if ip_address:
        ip_address = IPv4Address(mapped_action["ip_address"])
    target_session = mapped_action["target_session"]

    session = 0

    if mapped_action["name"] == "Sleep":
        action = Sleep()

    elif mapped_action["name"] == "Monitor":
        action = Monitor(session=session, agent="Blue")

    elif mapped_action["name"] == "Analyse":
        action = Analyse(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "Remove":
        action = Remove(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DecoyApache":
        action = DecoyApache(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DecoyFemitter":
        action = DecoyFemitter(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DecoyHarakaSMPT":
        action = DecoyHarakaSMPT(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DecoySmss":
        action = DecoySmss(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DecoySSHD":
        action = DecoySSHD(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DecoySvchost":
        action = DecoySvchost(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DecoyTomcat":
        action = DecoyTomcat(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DecoyVsftpd":
        action = DecoyVsftpd(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "Restore":
        action = Restore(hostname=hostname, session=session, agent="Blue")

    elif mapped_action["name"] == "DiscoverRemoteSystems":
        action = DiscoverRemoteSystems(session=session, agent="Red", subnet=subnet)

    elif mapped_action["name"] == "DiscoverNetworkServices":
        action = DiscoverNetworkServices(session=session, agent="Red", ip_address=ip_address)

    elif mapped_action["name"] == "ExploitRemoteService":
        if "priority" in mapped_action:
            priority = mapped_action["priority"]
            action = ExploitRemoteService(session=session, agent="Red", ip_address=ip_address, priority=priority)
        else:
            action = ExploitRemoteService(session=session, agent="Red", ip_address=ip_address)

    elif mapped_action["name"] == "PrivilegeEscalate":
        action = PrivilegeEscalate(session=session, agent="Red", hostname=hostname)

    elif mapped_action["name"] == "Impact":
        action = Impact(session=session, agent="Red", hostname=hostname)

    elif mapped_action["name"] == "BlueKeep":
        action = BlueKeep(session=session, agent="Red", target_session=target_session, ip_address=ip_address)

    elif mapped_action["name"] == "EternalBlue":
        action = EternalBlue(session=session, agent="Red", target_session=target_session, ip_address=ip_address)

    elif mapped_action["name"] == "FTPDirectoryTraversal":
        action = FTPDirectoryTraversal(session=session, agent="Red", target_session=target_session, ip_address=ip_address)

    elif mapped_action["name"] == "HarakaRCE":
        action = HarakaRCE(session=session, agent="Red", target_session=target_session, ip_address=ip_address)

    elif mapped_action["name"] == "HTTPRFI":
        action = HTTPRFI(session=session, agent="Red", target_session=target_session, ip_address=ip_address)

    elif mapped_action["name"] == "HTTPSRFI":
        action = HTTPSRFI(session=session, agent="Red", target_session=target_session, ip_address=ip_address)

    elif mapped_action["name"] == "SQLInjection":
        action = SQLInjection(session=session, agent="Red", target_session=target_session, ip_address=ip_address)

    elif mapped_action["name"] == "SSHBruteForce":
        action = SSHBruteForce(session=session, agent="Red", target_session=target_session, ip_address=ip_address)

    else:
        print("The action name in the dictionary does not correspond to any existing Cyborg action.")

    return action


class BlueTableRandom:
    def __init__(self):
        self.baseline = None
        self.blue_info = {}
        self.last_action = None
        self.info = None
        self.sort_hosts = []
        self.success = None

    def _process_initial_obs(self, obs):
        obs = obs.copy()
        self.baseline = obs
        del self.baseline["success"]
        for hostid in obs:
            if hostid == "success":
                continue
            host = obs[hostid]
            interface = host["Interface"][0]
            subnet = interface["Subnet"]
            ip = str(interface["IP Address"])
            hostname = host["System info"]["Hostname"]
            self.blue_info[hostname] = [str(subnet), str(ip), hostname, "None", "No"]
        return self.blue_info

    def observation_change(self, observation, last_action, baseline=False):
        self.last_action = last_action
        obs = observation if type(observation) == dict else observation.data
        obs = deepcopy(observation)
        self.success = obs["success"]

        self._process_last_action()
        anomaly_obs = self._detect_anomalies(obs) if not baseline else obs
        del obs["success"]
        # TODO check what info is for baseline
        info = self._process_anomalies(anomaly_obs)
        if baseline:
            for host in info:
                info[host][-2] = "None"
                info[host][-1] = "No"
                self.blue_info[host][-1] = "No"

        self.info = info

        return self._create_vector()

    def _process_last_action(self):
        action = self.last_action
        if action is not None:
            name = action.__class__.__name__
            hostname = action.get_params()["hostname"] if name in ("Restore", "Remove") else None

            if name == "Restore":
                self.blue_info[hostname][-1] = "No"
            elif name == "Remove":
                compromised = self.blue_info[hostname][-1]
                if compromised != "No":
                    self.blue_info[hostname][-1] = "Unknown"

    def _detect_anomalies(self, obs):
        if self.baseline is None:
            raise TypeError("BlueTableWrapper was unable to establish baseline. This usually means the environment was not reset before calling the step method.")

        anomaly_dict = {}

        for hostid, host in obs.items():
            if hostid == "success":
                continue

            host_baseline = self.baseline[hostid]
            if host == host_baseline:
                continue

            host_anomalies = {}
            if "Files" in host:
                baseline_files = host_baseline.get("Files", [])
                anomalous_files = []
                for f in host["Files"]:
                    if f not in baseline_files:
                        anomalous_files.append(f)
                if anomalous_files:
                    host_anomalies["Files"] = anomalous_files

            if "Processes" in host:
                baseline_processes = host_baseline.get("Processes", [])
                anomalous_processes = []
                for p in host["Processes"]:
                    if p not in baseline_processes:
                        anomalous_processes.append(p)
                if anomalous_processes:
                    host_anomalies["Processes"] = anomalous_processes

            if host_anomalies:
                anomaly_dict[hostid] = host_anomalies

        return anomaly_dict

    def _process_anomalies(self, anomaly_dict):
        info = deepcopy(self.blue_info)
        for hostid, host_anomalies in anomaly_dict.items():
            assert len(host_anomalies) > 0
            if "Processes" in host_anomalies:
                connection_type = self._interpret_connections(host_anomalies["Processes"])
                info[hostid][-2] = connection_type
                if connection_type == "Exploit":
                    info[hostid][-1] = "User"
                    self.blue_info[hostid][-1] = "User"
            if "Files" in host_anomalies:
                malware = [f["Density"] >= 0.9 for f in host_anomalies["Files"]]
                if any(malware):
                    info[hostid][-1] = "Privileged"
                    self.blue_info[hostid][-1] = "Privileged"

        return info

    def _interpret_connections(self, activity: list):
        num_connections = len(activity)

        ports = set([item["Connections"][0]["local_port"] for item in activity if "Connections" in item])
        port_focus = len(ports)

        remote_ports = set([item["Connections"][0].get("remote_port") for item in activity if "Connections" in item])
        if None in remote_ports:
            remote_ports.remove(None)

        if num_connections >= 3 and port_focus >= 3:
            anomaly = "Scan"
        elif 4444 in remote_ports:
            anomaly = "Exploit"
        elif num_connections >= 3 and port_focus == 1:
            anomaly = "Exploit"
        elif "Service Name" in activity[0]:
            anomaly = "None"
        else:
            anomaly = "Scan"

        return anomaly

    def _create_blue_table(self, success):
        table = PrettyTable(["Subnet", "IP Address", "Hostname", "Activity", "Compromised"])
        for hostid in self.info:
            table.add_row(self.info[hostid])

        table.sortby = "Hostname"
        table.success = success
        return table

    def add_nonexistent_hosts(self) -> list:
        full_hosts = []
        for s in range(max_subnets):
            for h in range(max_hosts):
                full_hosts.append(f"Subnet_{s}_Host_{h}")

        defender_subnet_number = 0
        for host in self.sort_hosts:
            if "Defender" in host:
                defender_subnet_number = host.split("_")[1]
                break

        # hosts that do not exist in short hosts are appended with not_exist in their name
        new_list = []
        for host in full_hosts:
            if host in self.sort_hosts:
                new_list.append(host)
            else:
                new_list.append("not_exist")

        # replace last not_exist host of last existing subnet with op_server
        op_server_subnet = self.sort_hosts[-1].split("_")[1]
        for host in reversed(new_list):
            if host != "not_exist" and new_list.index(host) != len(new_list):
                new_list[new_list.index(host) + 1] = f"Subnet_{op_server_subnet}_Op_Server"
                break

        # replace first host of defender subnet with defender.
        for host in full_hosts:
            if defender_subnet_number == host.split("_")[1]:
                new_list[full_hosts.index(host)] = f"Subnet_{defender_subnet_number}_Defender"
                break

        # Op always at the end
        new_chunk_list = [new_list[x : x + max_hosts] for x in range(0, len(new_list), max_hosts)]
        for chunk in range(len(new_chunk_list)):
            if any(["Op_Server" in element for element in new_chunk_list[chunk]]) and chunk != len(new_chunk_list):
                new_chunk_list[chunk], new_chunk_list[-1] = (
                    new_chunk_list[-1],
                    new_chunk_list[chunk],
                )
                for item in new_chunk_list[chunk]:
                    if "Op_Server" in item:
                        (
                            new_chunk_list[chunk][new_chunk_list[chunk].index(item)],
                            new_chunk_list[chunk][-1],
                        ) = (
                            new_chunk_list[chunk][-1],
                            new_chunk_list[chunk][new_chunk_list[chunk].index(item)],
                        )
                        break
        new_list = [j for i in new_chunk_list for j in i]

        return new_list

    def _create_vector(self):
        table = self._create_blue_table(self.success)._rows

        true_table = [next((y for y in table if y[2] == x), ["not_exist" for i in range(6)]) for x in self.sort_hosts]
        # pprint(true_table)
        # exit()
        success_value = int(self.success.value) if self.success.value < 2 else -1
        proto_vector = [success_value]

        for row in true_table:
            if row[0] != "not_exist":
                # Activity
                activity = row[3]
                if activity == "None":
                    value = [0, 0]
                elif activity == "Scan":
                    value = [1, 0]
                elif activity == "Exploit":
                    value = [1, 1]
                else:
                    raise ValueError("Table had invalid Access Level")
                proto_vector.extend(value)

                # Compromised
                compromised = row[4]
                if compromised == "No":
                    value = [0, 0]
                elif compromised == "Unknown":
                    value = [1, 0]
                elif compromised == "User":
                    value = [0, 1]
                elif compromised == "Privileged":
                    value = [1, 1]
                else:
                    raise ValueError("Table had invalid Access Level")
                proto_vector.extend(value)
            else:
                proto_vector.extend([-1, -1, -1, -1])

        return np.array(proto_vector)


class RedTableRandom:
    def __init__(self, action_mapping=None):
        self.red_info = {}
        self.known_subnets = set()
        self.step_counter = -1
        self.id_tracker = -1
        self.success = None
        self.last_action = None
        self.action_mapping = action_mapping
        self.sort_hosts = []
        self.true_table = []

    def observation_change(self, observation, last_action, action_mapping=None, true_obs=None):
        self.true_obs = true_obs
        self.last_action = last_action
        self.success = observation["success"]
        if action_mapping:
            self.action_mapping = action_mapping

        self.step_counter += 1
        if self.step_counter <= 0:
            self._process_initial_obs(observation)
        elif self.success:
            self._update_red_info(observation)

        obs = self._create_vector()

        return obs

    def _process_initial_obs(self, obs):
        for hostid in obs:
            if hostid == "success":
                continue
            host = obs[hostid]
            interface = host["Interface"][0]
            subnet = interface["Subnet"]
            self.known_subnets.add(subnet)
            ip = str(interface["IP Address"])
            hostname = host["System info"]["Hostname"]
            self.red_info[ip] = [str(subnet), str(ip), hostname, False, "Privileged"]

    def _update_red_info(self, obs):
        action = self.last_action
        name = action.__class__.__name__
        if name == "DiscoverRemoteSystems":
            self._add_ips(obs)
        elif name == "DiscoverNetworkServices":
            try:
                self._add_ips(obs)
            except:
                pass

            item = obs.popitem()[1]
            if isinstance(item, dict):
                interface = item.get("Interface", [])
                ip = str(interface[0]["IP Address"]) if interface and isinstance(interface, list) else None
                # print("IP is ", ip)
                if ip is not None:
                    self.red_info[ip][3] = True

        elif name == "ExploitRemoteService" or isinstance(action, ExploitAction):
            try:
                self._add_ips(obs)
            except:
                pass
            self._process_exploit(obs)
        elif name == "PrivilegeEscalate":
            try:
                self._add_ips(obs)
            except:
                pass
            hostname = action.hostname
            self._process_priv_esc(obs, hostname)

    def _add_ips(self, obs):
        for hostid in obs:
            if hostid == "success":
                continue
            host = obs[hostid]
            for interface in host["Interface"]:
                ip = interface["IP Address"]
                subnet = interface["Subnet"]
                if subnet not in self.known_subnets:
                    self.known_subnets.add(subnet)
                if str(ip) not in self.red_info:
                    subnet = self._get_subnet(ip)
                    hostname = self._generate_name("HOST")
                    self.red_info[str(ip)] = [subnet, str(ip), hostname, False, "None"]
                elif self.red_info[str(ip)][0].startswith("UNKNOWN_"):
                    self.red_info[str(ip)][0] = self._get_subnet(ip)

    def _get_subnet(self, ip):
        for subnet in self.known_subnets:
            if ip in subnet:
                return str(subnet)
        return self._generate_name("SUBNET")

    def _generate_name(self, datatype: str):
        self.id_tracker += 1
        unique_id = "UNKNOWN_" + datatype + ": " + str(self.id_tracker)
        return unique_id

    def _process_exploit(self, obs):
        for hostid in obs:
            if hostid == "success":
                continue

            host = obs[hostid]
            if "Sessions" in host:
                ip = str(host["Interface"][0]["IP Address"])
                if "System info" in host.keys():
                    hostname = host["System info"]["Hostname"]
                else:
                    hostname = hostid
                session = host["Sessions"][0]
                access = "Privileged" if "Username" in session and session["Username"] in ["root", "SYSTEM"] else "User"

                self.red_info[ip][2] = hostname
                self.red_info[ip][4] = access

    def _process_priv_esc(self, obs, hostname):
        if obs["success"] == False:
            red_info = [info for info in self.red_info.values() if info[2] == hostname]
            if len(red_info) > 0:
                red_info[0][4] = "None"
        else:
            for hostid in obs:
                if hostid == "success":
                    continue
                host = obs[hostid]
                ip = host["Interface"][0]["IP Address"]

                if "Sessions" in host:
                    access = "Privileged"
                    self.red_info[str(ip)][4] = access
                else:
                    subnet = self._get_subnet(ip)
                    hostname = self._generate_name("HOST")

                    if str(ip) not in self.red_info:
                        self.red_info[str(ip)] = [subnet, str(ip), hostname, False, "None"]
                    else:
                        self.red_info[str(ip)][0] = subnet
                        self.red_info[str(ip)][2] = hostname

    def _create_red_table(self):
        # The table data is all stored inside the ip nodes
        # which form the rows of the table
        table = PrettyTable(
            [
                "Subnet",
                "IP Address",
                "Hostname",
                "Scanned",
                "Access",
            ]
        )
        for ip in self.red_info:
            table.add_row(self.red_info[ip])

        table.sortby = "IP Address"
        table.success = self.success
        return table

    # takes list of existing hosts and appends it with not_exist hosts so that it matches the full host list provided.
    # the observations of the not_exist hosts are never updated, they just serve as placeholders so that if a host exists
    # in different scenarios, the observation about them are given in the same place.
    def add_nonexistent_hosts(self) -> list:
        full_hosts = []
        for s in range(max_subnets):
            for h in range(max_hosts):
                full_hosts.append(f"Subnet_{s}_Host_{h}")

        defender_subnet_number = 0
        for host in self.sort_hosts:
            if "Defender" in host:
                defender_subnet_number = host.split("_")[1]
                break

        # hosts that do not exist in short hosts are appended with not_exist in their name
        new_list = []
        for host in full_hosts:
            if host in self.sort_hosts:
                new_list.append(host)
            else:
                new_list.append("not_exist")

        # replace last not_exist host of last existing subnet with op_server
        op_server_subnet = self.sort_hosts[-1].split("_")[1]
        for host in reversed(new_list):
            if host != "not_exist" and new_list.index(host) != len(new_list):
                new_list[new_list.index(host) + 1] = f"Subnet_{op_server_subnet}_Op_Server"
                break

        # replace first host of defender subnet with defender.
        for host in full_hosts:
            if defender_subnet_number == host.split("_")[1]:
                new_list[full_hosts.index(host)] = f"Subnet_{defender_subnet_number}_Defender"
                break

        new_chunk_list = [new_list[x : x + max_hosts] for x in range(0, len(new_list), max_hosts)]
        for chunk in range(len(new_chunk_list)):
            if any(["Op_Server" in element for element in new_chunk_list[chunk]]) and chunk != len(new_chunk_list):
                new_chunk_list[chunk], new_chunk_list[-1] = new_chunk_list[-1], new_chunk_list[chunk]
                for item in new_chunk_list[chunk]:
                    if "Op_Server" in item:
                        new_chunk_list[chunk][new_chunk_list[chunk].index(item)], new_chunk_list[chunk][-1] = (
                            new_chunk_list[chunk][-1],
                            new_chunk_list[chunk][new_chunk_list[chunk].index(item)],
                        )
                        break
        new_list = [j for i in new_chunk_list for j in i]

        return new_list

    def _create_vector(self):  # 23 13
        table = self._create_red_table()._rows

        true_table = self.true_table  # self.get_table(output_mode="true_table").rows
        true_table = true_table.rows

        true_table = [next((y for y in true_table if y[2] == x), ["not_exist" for i in range(6)]) for x in self.sort_hosts]

        success_value = int(self.success.value) if self.success.value < 2 else -1
        proto_vector = [success_value]

        for i, row in enumerate(true_table):
            position = [i for i, t in enumerate(table) if row[1] in t]
            host_obs = []
            if position != []:
                # Scanned
                scanned = int(table[position[0]][3])
                host_obs.append(scanned)
                # Access
                access = table[position[0]][4]
                if access == "None":
                    value = [0, 0]
                elif access == "User":
                    if self.old_obs[1 + i * 3 + 1 : 1 + i * 3 + 2 + 1] == [0, 1]:  # i*4 if port22obs
                        value = [0, 1]
                    else:
                        value = [1, 0]
                elif access == "Privileged":
                    # if self.old_obs[1+i*3+1:1+i*3+2+1]==[1,0]or self.old_obs[1+i*3+1:1+i*3+2+1]==[1,1]: # i*4 if port22obs
                    #     value = [1, 1]
                    # else:
                    value = [0, 1]
                else:
                    raise ValueError("Table had invalid Access Level")
                host_obs.extend(value)

            else:
                host_obs = [-1, -1, -1]

            proto_vector.extend(host_obs)

        #     if len(proto_vector)%16==0 and len(proto_vector)!=64 :
        #         proto_vector.append(success_value)
        # print(proto_vector)
        self.old_obs = proto_vector
        proto_vector = np.array(proto_vector)

        # proto_vector=proto_vector.reshape((1,4,16))

        return proto_vector

    def get_table_from_action_mapping(self):
        true_table = []
        for k, v in self.action_mapping.items():
            if k != "status":
                if v["name"] == "DiscoverNetworkServices":
                    true_table.append([v["subnet"], v["ip_address"], v["hostname"]])

        return true_table

    def get_table_from_true_obs(self):
        true_table = []
        for k, v in self.true_obs.items():
            if k != "success":
                hostname = v["System info"]["Hostname"]
                subnet, ip_address = None, None
                for interface in v["Interface"]:
                    if "Interface Name" in interface.keys():
                        if interface["Interface Name"] != "lo":
                            subnet = interface["Subnet"]
                            ip_address = interface["IP Address"]
                            break
                true_table.append([subnet, ip_address, hostname])

        return true_table
