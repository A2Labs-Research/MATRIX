import random
import yaml
from CybORG import CybORG
import inspect
import numpy as np
import gymnasium as gym
import sys
import warnings
import uuid
import os
import inspect

sys.modules["gym"] = gym
warnings.filterwarnings("ignore")


class NoAliasDumper(yaml.Dumper):
    def ignore_aliases(self, data):
        return True


class RandomTopologySIS:
    def __init__(self, seed=None, scenario_name=None) -> None:
        # Scenario elements
        self.seed = seed
        self.hosts = []
        self.subnets = []
        self.agents = ["Blue", "Green", "Red"]

        # Scenario produced dicts
        self.hosts_dict = {}
        self.subnets_dict = {}
        self.agents_dict = {}
        self.services_dict = {}
        self.system_types = []
        self.max_subnets = 4
        self.max_hosts = 5
        self.defender_subnet_number=0
        if scenario_name:
            self.scenario_name = scenario_name
        else:
            self.scenario_name = str(uuid.uuid4())

        np.random.seed(seed)
        random.seed(seed)

    # Helper function to group hosts belonging to a specific subnet
    def find_subnet_hosts(self, subnet):
        my_list = []
        for host in self.hosts:
            if str(subnet + '_') in host:
                my_list.append(host)
        return my_list

    def create_subnet_host_lists(self):
        # Create Defender host on random subnet
        self.defender_subnet_number = 1

        # Create random number of subnets and hosts
        num_subnets = random.randint(3, self.max_subnets)  # 3, 4
        for s in range(num_subnets):
            self.subnets.append(str("Subnet_") + str(s))
            # Defender subnet must have at least 3 hosts
            if s == self.defender_subnet_number:
                if self.max_hosts >= 3:
                    num_hosts = random.randint(3, self.max_hosts)
                else:
                    num_hosts = 3
            elif s == num_subnets-1:
                num_hosts = random.randint(4, self.max_hosts)  # 4, 5
            else:
                num_hosts = random.randint(2, self.max_hosts)  # 2, 5
            for h in range(num_hosts):
                self.hosts.append("Subnet_" + str(s) + "_Host_" + str(h))

        # Replace the last host of the last subnet with server, front, auth, db
        self.hosts[-4] = "Subnet_" + str(s) + "_Op_Auth"
        self.hosts[-3] = "Subnet_" + str(s) + "_Op_Database"
        self.hosts[-2] = "Subnet_" + str(s) + "_Op_Front"
        self.hosts[-1] = "Subnet_" + str(s) + "_Op_Server"

        for host in self.hosts:
            if str(self.defender_subnet_number) in host[:10]:
                self.hosts[self.hosts.index(host)] = "Subnet_" + str(self.defender_subnet_number) + "_Defender"
                break
    
        self.hosts.sort()
        self.subnets.sort()

    def create_agents_dict(self):
        # Basic Agent dictionary structure
        agent_dict_keys = ["AllowedSubnets", "INT", "actions", "agent_type", "reward_calculator_type", "starting_sessions", "wrappers"]
        self.agents_dict = {"Agents": {agent: {subkey: {} for subkey in agent_dict_keys} for agent in self.agents}}

        # AllowedSubnets, agent_type and wrappers keys (Same for all agents)
        for agent in self.agents:
            self.agents_dict["Agents"][agent]["AllowedSubnets"] = self.subnets
            self.agents_dict["Agents"][agent]["agent_type"] = "SleepAgent"
            self.agents_dict["Agents"][agent]["wrappers"] = []

        # INT key (Same for Blue/Green, only the first initial host for Red)
        int_dict = {"Interfaces": "All", "System info": "All", "User info": "All"}
        self.agents_dict["Agents"]["Blue"]["INT"]["Hosts"] = {host: int_dict for host in self.hosts}
        self.agents_dict["Agents"]["Green"]["INT"]["Hosts"] = {host: int_dict for host in self.hosts}
        self.agents_dict["Agents"]["Red"]["INT"]["Hosts"] = {self.hosts[0]: {"Interfaces": "All", "System info": "All"}}

        # adversary key (Only for Blue)
        self.agents_dict["Agents"]["Blue"]["adversary"] = "Red"

        # actions key for all agents
        self.agents_dict["Agents"]["Blue"]["actions"] = [
            "Sleep",
            "Monitor",
            "Analyse",
            "Remove",
            "DecoyApache",
            "DecoyFemitter",
            "DecoyHarakaSMPT",
            "DecoySmss",
            "DecoySSHD",
            "DecoySvchost",
            "DecoyTomcat",
            "DecoyVsftpd",
            "Restore",
            #"Block"
        ]
        self.agents_dict["Agents"]["Green"]["actions"] = ["Sleep", "GreenPingSweep", "GreenPortScan", "GreenConnection","GreenConsumeService"]
        self.agents_dict["Agents"]["Red"]["actions"] = [
            "Sleep",
            "DiscoverRemoteSystems",
            "DiscoverNetworkServices",
            "ExploitRemoteService",
            "BlueKeep",
            "EternalBlue",
            "FTPDirectoryTraversal",
            "HarakaRCE",
            "HTTPRFI",
            "HTTPSRFI",
            "SQLInjection",
            "PrivilegeEscalate",
            "Impact",
            "SSHBruteForce",
        ]

        # reward_calculator_type key for all agents
        self.agents_dict["Agents"]["Blue"]["reward_calculator_type"] = "HybridAvailabilityConfidentiality"
        self.agents_dict["Agents"]["Green"]["reward_calculator_type"] = "Success"
        self.agents_dict["Agents"]["Red"]["reward_calculator_type"] = "HybridImpactPwn"

        # system_selection = random.choices(['ubuntu','SYSTEM'], weights=[0.8,0.2], k=1)[0]
        # starting_sessions
        self.agents_dict["Agents"]["Blue"]["starting_sessions"] = [
            {
                "hostname": host,
                "name": "Velo" + host,
                "parent": "VeloServer",
                "type": "VelociraptorClient",
                "username": random.choices(["ubuntu", "SYSTEM"], weights=[0.7, 0.3], k=1)[0],
            }
            for host in self.hosts
        ]

        for mylist in self.agents_dict["Agents"]["Blue"]["starting_sessions"]:
            if "Defender" in mylist["hostname"]:
                # find Defender hostname and system type from dict
                defender_hostname = mylist["hostname"]
                defender_system_type = mylist["username"]
                break
        self.agents_dict["Agents"]["Blue"]["starting_sessions"].append(
            {
                "artifacts": ["NetworkConnections", "ProcessCreation"],#, "SuspiciousActivity"],
                "hostname": defender_hostname,
                "name": "VeloServer",
                "num_children_sessions": 2,
                "type": "VelociraptorServer",
                "username": defender_system_type,
            }
        )
        self.agents_dict["Agents"]["Green"]["starting_sessions"] = [
            {"hostname": host, "name": "GreenSession", "type": "green_session", "username": "GreenAgent"} for host in self.hosts if host != defender_hostname
        ]
        self.agents_dict["Agents"]["Red"]["starting_sessions"] = [{"hostname": self.hosts[0], "name": "RedPhish", "type": "RedAbstractSession", "username": "SYSTEM"}]

        # list with the system type of each host
        system_types = []
        for i in range(len(self.hosts)):
            if self.agents_dict["Agents"]["Blue"]["starting_sessions"][i]["hostname"] == self.hosts[i]:
                system_types.append(self.agents_dict["Agents"]["Blue"]["starting_sessions"][i]["username"])

        # check that each subnet has hosts both windows and ubuntu hosts
        for subnet in self.subnets:
            # find the subnets' hosts and their system types
            host_list = self.find_subnet_hosts(subnet)
            system_type_list = [system_types[self.hosts.index(host)] for host in host_list]
            # if all of the hosts are ubuntu make the second one windows by updating agents_dict and system_types list
            if all(system_type == "ubuntu" for system_type in system_type_list):
                system_types[self.hosts.index(host_list[1])] = "SYSTEM"
                self.agents_dict["Agents"]["Blue"]["starting_sessions"][self.hosts.index(host_list[1])]["username"] = "SYSTEM"
                # print('changed this host: ',host_list[1])
            # if all of the hosts are ubuntu make the second one windows by updating agents_dict and system_types list
            if all(system_type == "SYSTEM" for system_type in system_type_list):
                system_types[self.hosts.index(host_list[1])] = "ubuntu"
                self.agents_dict["Agents"]["Blue"]["starting_sessions"][self.hosts.index(host_list[1])]["username"] = "ubuntu"
                # print('changed this host: ',host_list[1])
        return system_types

    def create_hosts_dict(self, system_types):
        # every_host
        self.hosts_dict = {"Hosts": {host: {} for host in self.hosts}}

        for host in self.hosts:
            if str(host)=='Subnet_0_Host_0':           
                self.hosts_dict["Hosts"][host] = {
                    "AWS_Info": [],  # choose image based on system type that is stored in system_types list fro every host
                    "image": (
                        random.choice(["linux_user_host1", "linux_user_host2"])
                        if system_types[self.hosts.index(host)] == "ubuntu"
                        else random.choice(["windows_user_host1", "windows_user_host2"])
                    ),
                    "info": {host: {"Interfaces": "All"}},
                    "ConfidentialityValue": "None",
                    "AvailabilityValue": "None",
                }
            # hosts belonging to operational subnet
            elif host.split("_")[1] == str(len(self.subnets) - 1):  # op_server_subnet_number
                if host.endswith("Op_Database"):
                    self.hosts_dict["Hosts"][host] = {"AWS_Info": [], "image": "OP_Database", 
                                                      "info": {host: {"Interfaces": "All", "Services": ["DBService"]}}, 
                                                      "ConfidentialityValue": "Medium", "AvailabilityValue": "High",}
                elif host.endswith("Op_Auth"):
                    self.hosts_dict["Hosts"][host] = {"AWS_Info": [], "image": "OP_Auth",
                                                      "info": {host: {"Interfaces": "All", "Services": ["AuthService"]}}, 
                                                      "ConfidentialityValue": "Medium", "AvailabilityValue": "High",}
                elif host.endswith("Op_Front"):
                    self.hosts_dict["Hosts"][host] = {"AWS_Info": [], "image": "OP_Front",
                                                      "info": {host: {"Interfaces": "All", "Services": ["WebFrontService"]}}, 
                                                      "ConfidentialityValue": "Medium", "AvailabilityValue": "High",}
                else:
                    self.hosts_dict["Hosts"][host] = {"AWS_Info": [], "image": "Gateway", "info": {host: {"Interfaces": "All"}}}

            # hosts belonging to defender = enterprise subnet
            elif host.split("_")[1] == str([host.split("_")[1] for host in self.hosts if "Defender" in host][0]):  # defender_subnet_number
                self.hosts_dict["Hosts"][host] = {
                    "AWS_Info": [],
                    "image": random.choice(["Internal", "Gateway"]),
                    "info": {host: {"Interfaces": "All"}},
                    "ConfidentialityValue": "Medium",
                    "AvailabilityValue": "Medium",
                }

            # host from every other subnet
            else:
                self.hosts_dict["Hosts"][host] = {
                    "AWS_Info": [],  # choose image based on system type that is stored in system_types list fro every host
                    "image": (
                        random.choice(["linux_user_host1", "linux_user_host2"])
                        if system_types[self.hosts.index(host)] == "ubuntu"
                        else random.choice(["windows_user_host1", "windows_user_host2"])
                    ),
                    "info": {host: {"Interfaces": "All"}},
                    "ConfidentialityValue": "Low",
                    "AvailabilityValue": "None",
                }

        # defender
        defender_host = [host for host in self.hosts if "Defender" in host][0]
        self.hosts_dict["Hosts"][defender_host] = {"AWS_Info": [], "image": "Velociraptor_Server"}

        # op_server is the last host in hosts list
        self.hosts_dict["Hosts"][self.hosts[-1]] = {
            "AWS_Info": [],
            "image": "OP_Server",
            "info": {self.hosts[-1]: {"Interfaces": "All", "Services": ["OTService"]}},
            "ConfidentialityValue": "Medium",
            "AvailabilityValue": "High",
        }

    def create_subnets_dict(self):
        self.subnets_dict = {"Subnets": {subnet: {} for subnet in self.subnets}}
        for subnet in self.subnets:
            # op_server_subnet
            if subnet[-1] == str(len(self.subnets) - 1):
                self.subnets_dict["Subnets"][subnet] = {
                    "Hosts": self.find_subnet_hosts(subnet),
                    "NACLs": {"User": {"in": "None", "out": "all"}, "all": {"in": "all", "out": "all"}},
                    "Size": len(self.find_subnet_hosts(subnet)),
                }
            # rest of subnets
            else:
                if self.subnets.index(subnet)==self.defender_subnet_number:
                    self.subnets_dict["Subnets"][subnet] = {
                    "Hosts": self.find_subnet_hosts(subnet),
                    "NACLs": {"all": {"in": "all", "out": "all"}},
                    "Size": len(self.find_subnet_hosts(subnet))-1,
                    }
                else:
                    self.subnets_dict["Subnets"][subnet] = {
                    "Hosts": self.find_subnet_hosts(subnet),
                    "NACLs": {"all": {"in": "all", "out": "all"}},
                    "Size": len(self.find_subnet_hosts(subnet)),
                    }

    def make_connections(self):
        connections_dict = {k: False for k in self.hosts}
        connections = []
        subnet_hosts_list_of_lists = []
        for subnet in self.subnets:
            subnet_hosts_list = self.find_subnet_hosts(subnet)
            subnet_hosts_list_of_lists.append(subnet_hosts_list)
        # print(subnet_hosts_list_of_lists)

        for i in range(len(self.subnets) - 1):
            # list of hosts prone to be connected from subnet
            source_list = [host for host in subnet_hosts_list_of_lists[i] if "Defender" not in host and connections_dict[host] is False and host != "Subnet_0_Host_0"]
            # select hosts to connect from subnet
            # 1 host min but max is hosts-1 so that there is always a host not connected t
            source_list_selected = random.choices(source_list, k=random.randint(1, len(source_list) - 1)) if len(source_list) > 1 else [source_list[0]]

            # list of hosts prone to be connected from next subnet
            target_list = [host for host in subnet_hosts_list_of_lists[i + 1] if "Defender" not in host and connections_dict[host] is False]
            # select hosts to connect from next subnet
            target_list_selected = random.choices(target_list, k=random.randint(1, len(target_list) - 1)) if len(target_list) > 1 else [target_list[0]]
            # 1 host min but max is hosts-1 so that there is always a host not connected t

            for host in source_list_selected:
                for target in target_list_selected:
                    if (
                        connections_dict[host] or connections_dict[target]
                    ):  # to avoid mistakes or put the same connection twice, because lists above can have the same element multiple times
                        continue
                    connections.append((host, target))
                    self.hosts_dict["Hosts"][host]["info"][target] = {"Interfaces": "IP Address"}
                    connections_dict[host], connections_dict[target] = True, True

    def create_topology(self):
        self.create_subnet_host_lists()
        self.system_types = self.create_agents_dict()
        self.create_hosts_dict(self.system_types)
        self.create_subnets_dict()
        self.make_connections()

        # Topology directory path
        topo_dir = os.path.join(str(inspect.getfile(CybORG))[:-10], "Shared/Scenarios/Random_Topologies_SIS")
        # Ensure the directory exists
        os.makedirs(topo_dir, exist_ok=True)
        # Define the file path
        new_yaml_file = os.path.join(topo_dir, f"{self.scenario_name}.yaml")

        # # YAML file paths
        # new_yaml_file = str(inspect.getfile(CybORG))[:-10] + "/Shared/Scenarios/Random_Topologies_SIS/" + self.scenario_name + ".yaml"

        with open(new_yaml_file, "w") as file:
            yaml.dump(self.agents_dict, file, Dumper=NoAliasDumper, default_flow_style=False)
            yaml.dump(self.hosts_dict, file, Dumper=NoAliasDumper, default_flow_style=False)
            yaml.dump(self.subnets_dict, file, Dumper=NoAliasDumper, default_flow_style=False)
        # print("\n\nrandom_scenario.yaml generated")
        # print(self.scenario_name)
        return new_yaml_file
