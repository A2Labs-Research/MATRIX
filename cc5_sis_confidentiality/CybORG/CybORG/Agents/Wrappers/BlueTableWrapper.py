from copy import deepcopy
from prettytable import PrettyTable
import numpy as np
import inspect
import yaml
from rich import print

from CybORG import CybORG
from CybORG.Shared.Results import Results
from CybORG.Agents.Wrappers.BaseWrapper import BaseWrapper
from CybORG.Agents.Wrappers.TrueTableWrapper import TrueTableWrapper

max_subnets = 4
max_hosts = 5


class BlueTableWrapper(BaseWrapper):
    def __init__(self, env=None, agent=None, output_mode="table", scenario_path=str(inspect.getfile(CybORG))[:-10] + "/Shared/Scenarios/Scenario2.yaml", paddings=False):
        super().__init__(env, agent, paddings)
        self.paddings = paddings
        self.env = TrueTableWrapper(env=env, agent=agent, paddings=self.paddings)
        self.agent = agent
        self.scenario_path = scenario_path
        self.success = None
        self.baseline = None
        self.output_mode = output_mode
        self.blue_info = {}
        self.previous_blue_info = {}
        self.host_info = {"Subnet": "", "IP": "", "Hostname": "", "Activity": "", "Compromised": "", "Alert": ""}
        self.scenario_data = None

    def reset(self, agent="Blue"):
        result = self.env.reset(agent)
        self.scenario_data = None
        obs = result.observation
        self.success = None
        if agent == "Blue":
            self._process_initial_obs(obs)
            obs = self.observation_change(obs, baseline=True)
        result.observation = obs
        return result

    def step(self, agent=None, action=None) -> Results:
        result = self.env.step(agent, action)
        obs = result.observation
        if agent == "Blue":
            obs = self.observation_change(obs)
        result.observation = obs
        result.action_space = self.action_space_change(result.action_space)
        return result

    # Initialize topology blue_info with initial values
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
            self.blue_info[hostname] = {"Subnet": str(subnet), "IP": str(ip), "Hostname": hostname, "Activity": "None", "Compromised": "No", "Alert": False}
            self.previous_blue_info[hostname] = {"Subnet": str(subnet), "IP": str(ip), "Hostname": hostname, "Activity": "None", "Compromised": "No", "Alert": False}

    def observation_change(self, observation, baseline=False):
        obs = observation if type(observation) == dict else observation.data
        obs = deepcopy(observation)
        del obs["success"]
        self.success = observation["success"]

        # Check latest Blue action and edit blue_info
        self._process_last_action()

        # Check for anomalies (additions) between init and current obs
        if not baseline:
            anomaly_obs = self._detect_anomalies(obs)
        else:
            anomaly_obs = obs
        info = self._process_anomalies(anomaly_obs)

        if baseline:
            for host in info:
                info[host]["Activity"] = "None"
                info[host]["Compromised"] = "No"
                info[host]["Alert"] = False
                self.blue_info[host]["Compromised"] = "No"

        self.info = info
        self.previous_blue_info = deepcopy(self.blue_info)

        if self.output_mode == "table":
            return self._create_blue_table(self.success)
        elif self.output_mode == "anomaly":
            anomaly_obs["success"] = self.success
            return anomaly_obs
        elif self.output_mode == "raw":
            return observation
        elif self.output_mode == "vector":
            return self._create_vector(self.success)
        else:
            raise NotImplementedError("Invalid output_mode for BlueTableWrapper")

    def get_table(self, output_mode="blue_table"):
        if output_mode == "blue_table":
            return self._create_blue_table(success=None)
        elif output_mode == "true_table":
            return self.env.get_table()

    # Get latest action and change the blue_info values accordingly
    def _process_last_action(self):
        action = self.get_last_action(agent="Blue")
        if action is not None:
            name = action.__class__.__name__
            hostname = action.get_params()["hostname"] if name in ("Restore", "Remove") else None

            # Restore sets Compromise to 'No'
            if name == "Restore" and self.success:
                self.blue_info[hostname]["Compromised"] = "No"
            # Remove sets Compromise to Unknown
            elif name == "Remove":
                compromised = self.blue_info[hostname]["Compromised"]
                if compromised != "No" and self.success:
                    self.blue_info[hostname]["Compromised"] = "Unknown"

    # Detect additions to the current observation in comparison to the initial observation
    def _detect_anomalies(self, obs):
        if self.baseline is None:
            raise TypeError("BlueTableWrapper was unable to establish baseline. This usually means the environment was not reset before calling the step method.")

        anomaly_dict = {}

        for hostid, host in obs.items():
            if hostid in ["success", "Network Activity"]:
                continue
            else:
                host_baseline = self.baseline[hostid]
            host_anomalies = {}
            if host == host_baseline:
                continue

            # Add new Files to anomalies
            if "Files" in host:
                baseline_files = host_baseline.get("Files", [])
                anomalous_files = []
                for f in host["Files"]:
                    if f not in baseline_files:
                        anomalous_files.append(f)
                if anomalous_files:
                    host_anomalies["Files"] = anomalous_files

            # Add new Processes to anomalies
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

        # Add new Network Activity to anomalies
        if "Network Activity" in obs.keys():
            anomalous_activities = obs["Network Activity"]
            for key, value in self.blue_info.items():
                if value['IP'] == anomalous_activities[0]['IP Address']:
                    hostid = key
                    break
            anomaly_dict[hostid] = anomalous_activities

        return anomaly_dict

    # Get all anomalies and set values in blue_info
    def _process_anomalies(self, anomaly_dict):
        info = deepcopy(self.blue_info)
        for hostid, host_anomalies in anomaly_dict.items():
            assert len(host_anomalies) > 0
            # New processes result in exploited host
            if "Processes" in host_anomalies:
                connection_type = self._interpret_connections(host_anomalies["Processes"])
                info[hostid]["Activity"] = connection_type
                if connection_type == "Exploit":
                    info[hostid]["Compromised"] = "User"
                    self.blue_info[hostid]["Compromised"] = "User"

            # New files result to privileged host
            if "Files" in host_anomalies:
                malware = [f["Density"] >= 0.9 for f in host_anomalies["Files"]]
                if any(malware):
                    info[hostid]["Compromised"] = "Privileged"
                    self.blue_info[hostid]["Compromised"] = "Privileged"

        # New files result to privileged host
        if "Network Activity" in anomaly_dict.keys():
            for key, value in self.blue_info.items():
                if value['IP'] == str(anomaly_dict["Network Activity"][0]['IP Address']):
                    hostid = key
                    break
            self.blue_info[hostid]["Alert"] = True

        return info

    # Gather anomalies connection and check host status
    def _interpret_connections(self, activity: list):
        num_connections = len(activity)

        try:
            remote_ports = set()
            local_ports = set()
            for item in activity:
                if "Connections" in item:
                    if "remote_port" in item["Connections"][0]:
                        local_ports.add(item["Connections"][0]["local_port"])
                        remote_ports.add(item["Connections"][0]["remote_port"])
                    else:
                        pass
        except Exception as e:
            print(activity)
            raise e

        port_focus = len(local_ports)
        if None in remote_ports:
            remote_ports.remove(None)
        elif num_connections >= 3 and port_focus >= 3:
            activity = "Scan"
        elif 4444 in remote_ports:
            activity = "Exploit"
        elif num_connections >= 3 and port_focus == 1:
            activity = "Exploit"
        elif "Service Name" in activity[0]:
            activity = "None"
        else:
            activity = "Scan"

        return activity

    def _create_blue_table(self, success):
        table = PrettyTable(["Subnet", "IP Address", "Hostname", "Activity", "Compromised", "Alert"])
        for hostid in self.info:
            row = list(self.info[hostid].values())
            table.add_row(row)
        table.sortby = "Hostname"
        table.success = success
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

    def _create_vector(self, success):
        table = self._create_blue_table(success)._rows
        # true_table = self.get_table(output_mode='true_table').rows

        if self.paddings:
            if self.scenario_data == None:
                with open(self.scenario_path, "r") as file:
                    self.scenario_data = yaml.safe_load(file)
            sort_hosts = self.scenario_data["Subnets"]
            sort_hosts = self.add_nonexistent_hosts(sort_hosts)
            true_table = [next((y for y in table if y[2] == x), ["not_exist" for i in range(6)]) for x in sort_hosts]
        else:
            if self.scenario_data == None:
                with open(self.scenario_path, "r") as file:
                    self.scenario_data = yaml.safe_load(file)
            sort_hosts = list(self.scenario_data["Hosts"].keys())  ######list
            true_table = [y for x in sort_hosts for y in table if y[2] == x]

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

                # Suspicious Network Activity Alert
                alert = row[5]
                if alert:
                    value = [1]
                else:
                    value = [0]
                proto_vector.extend(value)
            else:
                proto_vector.extend([-1, -1, -1, -1, -1])

        return np.array(proto_vector)

    def get_attr(self, attribute: str):
        return self.env.get_attr(attribute)

    def get_observation(self, agent: str):
        if agent == "Blue" and self.output_mode == "table":
            output = self.get_table()
        else:
            output = self.get_attr("get_observation")(agent)

        return output

    def get_agent_state(self, agent: str):
        return self.get_attr("get_agent_state")(agent)

    def get_action_space(self, agent):
        return self.env.get_action_space(agent)

    def get_last_action(self, agent):
        return self.get_attr("get_last_action")(agent)

    def get_ip_map(self):
        return self.get_attr("get_ip_map")()

    def get_rewards(self):
        return self.get_attr("get_rewards")()
