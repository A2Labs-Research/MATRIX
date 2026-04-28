import math
from copy import deepcopy
from prettytable import PrettyTable
import numpy as np
from pprint import pprint
from rich import print
from CybORG import CybORG
import inspect
from CybORG.Agents.Wrappers.BaseWrapper import BaseWrapper
from CybORG.Agents.Wrappers.TrueTableWrapper import TrueTableWrapper
from CybORG.Shared.Actions.ConcreteActions.ExploitAction import ExploitAction
from CybORG.Shared.Enums import TrinaryEnum
import yaml
from CybORG.Shared.Results import Results

max_subnets = 4
max_hosts = 5


class RedTableWrapper(BaseWrapper):
    def __init__(self, env=None, agent=None, output_mode="table", scenario_path=str(inspect.getfile(CybORG))[:-10] + "/Shared/Scenarios/Scenario2.yaml", paddings=False):
        super().__init__(env, agent, paddings)
        self.paddings = paddings
        self.env = TrueTableWrapper(env=env, agent=agent, paddings=self.paddings)
        self.agent = agent
        self.scenario_path = scenario_path
        self.red_info = {}
        self.known_subnets = set()
        self.step_counter = -1
        self.id_tracker = -1
        self.output_mode = output_mode
        self.success = None
        self.old_obs = []
        self.scenario_data = None

    def reset(self, agent=None):
        self.scenario_data = None
        self.red_info = {}
        self.known_subnets = set()
        self.step_counter = -1
        self.id_tracker = -1
        self.success = None
        result = self.env.reset(agent)
        if agent == "Red":
            obs = self.observation_change(result.observation)
            result.observation = obs
        return result

    def step(self, agent=None, action=None) -> Results:
        result = self.env.step(agent, action)
        obs = result.observation
        if agent == "Red":
            obs = self.observation_change(obs)
        result.observation = obs
        result.action_space = self.action_space_change(result.action_space)
        return result

    def get_table(self, output_mode="red_table"):
        if output_mode == "red_table":
            return self._create_red_table()
        elif output_mode == "true_table":
            return self.env.get_table()

    def observation_change(self, observation):
        self.success = observation["success"]

        self.step_counter += 1
        if self.step_counter <= 0:
            self._process_initial_obs(observation)
        elif self.success == TrinaryEnum.TRUE:
            self._update_red_info(observation)

        if self.output_mode == "table":
            obs = self._create_red_table()
        elif self.output_mode == "vector":
            obs = self._create_vector()
        elif self.output_mode == "raw":
            obs = observation
        else:
            raise NotImplementedError("Invalid output_mode")

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
            self.red_info[ip] = {'Subnet': str(subnet), 'IP': str(ip), 'Hostname': hostname, 'Scanned': False, 'Access': "Privileged"}

    def _update_red_info(self, obs):
        action = self.get_last_action(agent="Red")
        name = action.__class__.__name__
        if name == "DiscoverRemoteSystems":
            self._add_ips(obs)
        elif name == "DiscoverNetworkServices":
            item = obs.popitem()[1]
            if isinstance(item, dict):
                interface = item.get("Interface", [])
                ip = str(interface[0]["IP Address"]) if interface and isinstance(interface, list) else None
                if ip is not None:
                    self.red_info[ip]['Scanned'] = True

        elif name == "ExploitRemoteService" or isinstance(action, ExploitAction):
            self._process_exploit(obs)
        elif name == "PrivilegeEscalate":
            hostname = action.hostname
            self._process_priv_esc(obs, hostname)

    def _generate_name(self, datatype: str):
        self.id_tracker += 1
        unique_id = "UNKNOWN_" + datatype + ": " + str(self.id_tracker)
        return unique_id

    def _add_ips(self, obs):
        for hostid in obs:
            if hostid == "success":
                continue
            host = obs[hostid]
            for interface in host["Interface"]:
                ip = interface["IP Address"]
                subnet = interface["Subnet"]
                ip_str = str(ip)
                if subnet not in self.known_subnets:
                    self.known_subnets.add(subnet)
                if ip_str not in self.red_info.keys():
                    subnet = self._get_subnet(ip)
                    hostname = self._generate_name("HOST")
                    self.red_info[ip_str] = {'Subnet': subnet, 'IP': ip_str, 'Hostname': hostname, 'Scanned': False, 'Access': "None"}
                elif self.red_info[ip_str]['Subnet'].startswith("UNKNOWN_"):
                    self.red_info[ip_str]['Subnet'] = self._get_subnet(ip)

    def _get_subnet(self, ip):
        for subnet in self.known_subnets:
            if ip in subnet:
                return str(subnet)
        return self._generate_name("SUBNET")

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

                self.red_info[ip]['Hostname'] = hostname
                self.red_info[ip]['Access'] = access
            else:
                ip = str(host["Interface"][0]["IP Address"])
                hostname = hostid
                self.id_tracker += 1
                unique_id = "UNKNOWN_SUBNET: " + str(self.id_tracker)
                ip_str = str(ip)
                if ip_str not in self.red_info.keys():
                    subnet = unique_id
                    self.red_info[ip_str] = {'Subnet': subnet, 'IP': ip_str, 'Hostname': hostname, 'Scanned': False, 'Access': "None"}

    def _process_priv_esc(self, obs, hostname):
        if obs["success"] == False:
            red_info = [info for info in self.red_info.values() if info['Hostname'] == hostname]
            if len(red_info) > 0:
                red_info[0]['Access'] = "None"
        else:
            for hostid in obs:
                if hostid == "success":
                    continue
                host = obs[hostid]
                ip = host["Interface"][0]["IP Address"]
                ip_str = str(ip)

                if "Sessions" in host:
                    access = "Privileged"
                    self.red_info[ip_str]['Access'] = access
                else:
                    subnet = self._get_subnet(ip)
                    hostname = self._generate_name("HOST")

                    if ip_str not in self.red_info.keys():
                        self.red_info[ip_str] = {'Subnet': subnet, 'IP': ip_str, 'Hostname': hostname, 'Scanned': False, 'Access': "None"}
                    else:
                        self.red_info[ip_str]['Subnet'] = subnet
                        self.red_info[ip_str]['Hostname'] = hostname

    def _create_red_table(self):
        # The table data is all stored inside the ip nodes
        # which form the rows of the table
        table = PrettyTable(["Subnet", "IP Address", "Hostname", "Scanned", "Access",])
        for ip, value in self.red_info.items():
            table.add_row(list(value.values()))

        table.sortby = "IP Address"
        table.success = self.success
        return table

    # takes list of existing hosts and appends it with not_exist hosts so that it matches the full host list provided.
    # the observations of the not_exist hosts are never updated, they just serve as placeholders so that if a host exists
    # in different scenarios, the observation about them are given in the same place.
    def add_nonexistent_hosts(self, sort_hosts: dict) -> list:
        new_list = []
        for sub_name, sub_value in sort_hosts.items():
            sub_list = []
            server_host, defender_host = None, None
            for host in sub_value["Hosts"]:
                if "Server" in host:
                    server_host = host
                elif "Defender" in host:
                    defender_host = host
                else:
                    sub_list.append(host)
            while len(sub_list) < max_hosts:
                sub_list.append("not_exist")
            if server_host:
                sub_list[-1] = server_host
            if defender_host:
                sub_list[-1] = defender_host
                sub_list = [sub_list[-1]] + sub_list[:-1]
            new_list.extend(sub_list)

        while len(new_list) < max_hosts * max_subnets:
            empty_sub = ["not_exist"] * max_hosts
            start = new_list[: (max_hosts * (max_subnets - 2))]
            end = new_list[(max_hosts * (max_subnets - 2)) :]
            new_list = start + empty_sub + end

        # new_list.sort()
        new_chunk_list = [new_list[x : x + max_hosts] for x in range(0, len(new_list), max_hosts)]
        new_chunk_list.sort()
        for chunk in range(len(new_chunk_list)):
            if any(["Server" in element for element in new_chunk_list[chunk]]) and chunk != len(new_chunk_list):
                new_chunk_list[chunk], new_chunk_list[-1] = new_chunk_list[-1], new_chunk_list[chunk]
                for item in new_chunk_list[chunk]:
                    if "Server" in item:
                        new_chunk_list[chunk][new_chunk_list[chunk].index(item)], new_chunk_list[chunk][-1] = (
                            new_chunk_list[chunk][-1],
                            new_chunk_list[chunk][new_chunk_list[chunk].index(item)],
                        )
                        break
        new_list = [j for i in new_chunk_list for j in i]
        return new_list

    def _create_vector(self):  # 23 13
        table = self._create_red_table()._rows
        true_table = self.get_table(output_mode="true_table").rows
        
        if self.scenario_data == None:
            with open(self.scenario_path, "r") as file:
                self.scenario_data = yaml.safe_load(file)
        if self.paddings:
            sort_hosts = self.scenario_data["Subnets"]
            sort_hosts = self.add_nonexistent_hosts(sort_hosts)
            true_table = [next((y for y in true_table if y[2] == x), ["not_exist" for i in range(6)]) for x in sort_hosts]
        else:
            sort_hosts = list(self.scenario_data["Hosts"].keys())  ######list
            true_table = [y for x in sort_hosts for y in true_table if y[2] == x]

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
                    value = [0, 1]
                else:
                    raise ValueError("Table had invalid Access Level")
                host_obs.extend(value)

            else:
                host_obs = [-1, -1, -1]

            proto_vector.extend(host_obs)
        self.old_obs = proto_vector
        return np.array(proto_vector)

    def get_attr(self, attribute: str):
        return self.env.get_attr(attribute)

    def get_observation(self, agent: str):
        if agent != "Red" or self.output_mode == "raw":
            obs = self.get_attr("get_observation")(agent)
        elif self.output_mode == "table":
            obs = self.get_table()
        elif self.output_mode == "vector":
            obs = self._create_vector()
        else:
            raise NotImplementedError("Invalid output_mode")

        return obs

    def get_agent_state(self, agent: str):
        return self.get_attr("get_agent_state")(agent)

    def get_action_space(self, agent):
        return self.get_attr("get_action_space")(agent)

    def get_last_action(self, agent):
        return self.get_attr("get_last_action")(agent)

    def get_ip_map(self):
        return self.get_attr("get_ip_map")()

    def get_rewards(self):
        return self.get_attr("get_rewards")()
