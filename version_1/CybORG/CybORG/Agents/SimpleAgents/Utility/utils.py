# Utility functions to support extanded library of agents
from CybORG.Shared import ActionSpace
from copy import deepcopy
from prettytable import PrettyTable
import inspect
from CybORG.Shared.Actions import *
import numpy as np
import math
from ipaddress import IPv4Network, IPv4Address

class ActionMapping():
    def __init__(self):
        self.action_signature = {}
        self.possible_actions = None
        self.action_space = None
        self.scanned_ips = set()


    def action_mapping(self, action_space, true_obs):
        self.action_space = action_space
        list_of_actions = self.action_space_change(action_space)
        true_table = self.get_agent_state(true_obs)
        true_table_dict = self.prettytable_to_dict(true_table)
        dict_to_return={"status":"success"}
        for i in range(len(list_of_actions)):
            action_dict = self.identify_action(list_of_actions[i], true_table_dict,i)
            dict_to_return[i] = action_dict
        
        return dict_to_return
    
    def action_space_change(self, action_space: dict) -> list:
        assert type(action_space) is dict, \
            f"Wrapper required a dictionary action space. " \
            f"Please check that the wrappers below the ReduceActionSpaceWrapper return the action space as a dict "
        possible_actions = []
        temp = {}
        params = ['action']
        # for action in action_space['action']:
        for i, action in enumerate(action_space['action']):
            if action not in self.action_signature:
                self.action_signature[action] = inspect.signature(action).parameters
            param_list = [{}]
            for p in self.action_signature[action]:
                if p == 'priority':
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
                            #print('Key is', key, '  Val is', val)
                            p_dict[p] = key
                            new_param_list.append({key: value for key, value in p_dict.items()})
                    param_list = new_param_list
            for p_dict in param_list:
                possible_actions.append(action(**p_dict))
        #self.possible_actions = possible_actions
        max_target_session_present = self.find_max_target_session(possible_actions)
        self.possible_actions = self.organize_actions_based_on_session(possible_actions, max_target_session_present)
        return self.possible_actions

    def find_max_target_session(self,possible_actions:list)->int:
        """This function aims to find the max target session available in possible actions
        Args:
            possible_actions (list): all possible
        Returns:
            int: max target session available
        """
        # Assuming ActionSpace.MAX_SESSIONS is a predefined constant
        max_target_session_present:int = ActionSpace.MAX_SESSIONS
        for action in possible_actions:
            try:
                temp_target_session = action.target_session
                if temp_target_session > max_target_session_present:
                    max_target_session_present = temp_target_session
            except Exception as e:
                # Exception ignored, continue with next action
                pass
        return max_target_session_present

    def organize_actions_based_on_session(self, possible_actions:list, max_target_session_present:int)->list:
        """This function aims to order the new possible actions without touching the initial ordering till 888 (for MAX_SESSIONS = 8)
        Args:
            possible_actions (list): list of all possible actions
            max_target_session_present (int): max targets session
        Returns:
            list: newly ordered list
        """
        if possible_actions is None:
            possible_actions = []
        old_action_list:list = []
        new_action_list:list = []
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
            for i in range(ActionSpace.MAX_SESSIONS, max_target_session_present + 1):
                for action in new_action_list:
                    if action.target_session == i:
                        old_action_list.append(action)
            self.possible_actions = old_action_list
        return self.possible_actions
    
    def get_agent_state(self, true_obs):
        output = self.get_table(true_obs)
        return output
    
    def get_table(self, true_obs):
        return self._create_true_table(true_obs)
    
    def _create_true_table(self, true_obs):
        # true_obs = deepcopy(self.env.get_agent_state('True'))
        success = true_obs.pop('success')

        table = PrettyTable([
            'Subnet',
            'IP Address',
            'Hostname',
            'Known',
            'Scanned',
            'Access',
            ])

        for hostid in true_obs:
            host = true_obs[hostid]
            for interface in host['Interface']:
                ip = interface['IP Address']
                if str(ip) == '127.0.0.1':
                    continue
                if 'Subnet' not in interface:
                    continue
                subnet = interface['Subnet']
                hostname = host['System info']['Hostname']
                #  action_space = self.get_action_space(agent = 'Red')
                known = self.action_space['ip_address'][ip]
                scanned = True if str(ip) in self.scanned_ips else False
                access = self._determine_red_access(host['Sessions'])

                table.add_row([subnet,str(ip),hostname,known,scanned,access])
        
        table.sortby = 'Hostname'
        table.success = success
        return table

    def _determine_red_access(self,session_list):
        for session in session_list:
            if session['Agent'] != 'Red':
                continue
            privileged = session['Username'] in {'root','SYSTEM'}
            return 'Privileged' if privileged else 'User'

        return 'None'
    

    def prettytable_to_dict(self, table):
        headers = table.field_names
        table_str = str(table)
        rows = table_str.split('\n')[2:-1]  # Split the table string by newlines and exclude the header and footer
        data = []
        for row in rows:
            row_data = {}
            cells = row.split('|')[1:-1]  # Split the row by pipes and exclude empty cells and separators
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
        subnet=""
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
        if target_session =="":
            try:
                target_session = action.target_session
            except:
                pass
        dict_to_return= {
                        "number":number,
                        "name": action_name,
                        "hostname": hostname,
                        "ip_address": ip_address,
                        "subnet": subnet,
                        "target_session":target_session}
        return dict_to_return

    def get_based_on_hostname(self, hostname, table_dict):
        for dictionary in table_dict:
            if dictionary["Hostname"] == hostname:
                return str(dictionary["IP Address"]), str(dictionary["Subnet"])

    def get_based_on_ip_address(self, ip_address, table_dict):
        for dictionary in table_dict:
            if dictionary["IP Address"] == str(ip_address):
                return dictionary["Hostname"], str(dictionary["Subnet"])


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
        action = Monitor(session=session, agent='Blue')
    
    elif mapped_action["name"] == "Analyse":
        action = Analyse(hostname = hostname, session=session, agent='Blue')
    
    elif mapped_action["name"] == "Remove":
        action = Remove(hostname = hostname, session=session, agent='Blue')
    
    elif mapped_action["name"] == "DecoyApache":
        action = DecoyApache(hostname = hostname, session=session, agent='Blue')
    
    elif mapped_action["name"] == "DecoyFemitter":
        action = DecoyFemitter(hostname = hostname, session=session, agent='Blue')
    
    elif mapped_action["name"] == "DecoyHarakaSMPT":
        action = DecoyHarakaSMPT(hostname = hostname, session=session, agent='Blue')

    elif mapped_action["name"] == "DecoySmss":
        action = DecoySmss(hostname = hostname, session=session, agent='Blue')

    elif mapped_action["name"] == "DecoySSHD":
        action = DecoySSHD(hostname = hostname, session=session, agent='Blue')

    elif mapped_action["name"] == "DecoySvchost":
        action = DecoySvchost(hostname = hostname, session=session, agent='Blue')

    elif mapped_action["name"] == "DecoyTomcat":
        action = DecoyTomcat(hostname = hostname, session=session, agent='Blue')

    elif mapped_action["name"] == "DecoyVsftpd":
        action = DecoyVsftpd(hostname = hostname, session=session, agent='Blue')

    elif mapped_action["name"] == "Restore":
        action = Restore(hostname = hostname, session=session, agent='Blue')
    
    elif mapped_action["name"] == "DiscoverRemoteSystems":
        action = DiscoverRemoteSystems(session=session, agent = "Red", subnet=subnet)
    
    elif mapped_action["name"] == "DiscoverNetworkServices":
        action = DiscoverNetworkServices(session=session, agent = "Red", ip_address=ip_address)
    
    elif mapped_action["name"] == "ExploitRemoteService":
        if "priority" in mapped_action:
            priority = mapped_action["priority"]
            action = ExploitRemoteService(session=session, agent = "Red", ip_address=ip_address, priority=priority)
        else:
            action = ExploitRemoteService(session=session, agent = "Red", ip_address=ip_address)
    
    elif mapped_action["name"] == "PrivilegeEscalate":
        action = PrivilegeEscalate(session=session, agent = "Red", hostname=hostname)

    elif mapped_action["name"] == "Impact":
        action = Impact(session=session, agent = "Red", hostname=hostname)
    
    elif mapped_action["name"] == "BlueKeep":
        action = BlueKeep(session=session, agent = "Red", target_session = target_session, ip_address=ip_address)

    elif mapped_action["name"] == "EternalBlue":
        action = EternalBlue(session=session, agent = "Red", target_session = target_session, ip_address=ip_address)
    
    elif mapped_action["name"] == "FTPDirectoryTraversal":
        action = FTPDirectoryTraversal(session=session, agent = "Red", target_session = target_session, ip_address=ip_address)
    
    elif mapped_action["name"] == "HarakaRCE":
        action = HarakaRCE(session=session, agent = "Red", target_session = target_session, ip_address=ip_address)
    
    elif mapped_action["name"] == "HTTPRFI":
        action = HTTPRFI(session=session, agent = "Red", target_session = target_session, ip_address=ip_address)
    
    elif mapped_action["name"] == "HTTPSRFI":
        action = HTTPSRFI(session=session, agent = "Red", target_session = target_session, ip_address=ip_address)
    
    elif mapped_action["name"] == "SQLInjection":
        action = SQLInjection(session=session, agent = "Red", target_session = target_session, ip_address=ip_address)
    
    elif mapped_action["name"] == "SSHBruteForce":
        action = SSHBruteForce(session=session, agent = "Red", target_session = target_session, ip_address=ip_address)

    else:
        print("The action name in the dictionary does not correspond to any existing Cyborg action.")
    
    return action


class RedTable():
    def __init__(self):
        self.red_info = {}
        self.known_subnets = set()
        self.step_counter = -1
        self.id_tracker = -1
        self.success = None
        self.last_action = None
    
    def observation_change(self, observation, last_action):
        self.last_action = last_action
        self.success = observation['success']

        self.step_counter += 1
        if self.step_counter <= 0:
            self._process_initial_obs(observation)
        elif self.success:
            self._update_red_info(observation)

        obs = self._create_vector()

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
        action = self.last_action
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
                    
        elif name == 'ExploitRemoteService':
            self._process_exploit(obs)
        elif name == 'PrivilegeEscalate':
            hostname = action.hostname
            self._process_priv_esc(obs, hostname)
    
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
    
    def _generate_name(self, datatype: str):
        self.id_tracker += 1
        unique_id = 'UNKNOWN_' + datatype + ': ' + str(self.id_tracker)
        return unique_id

    def _process_exploit(self, obs):
        for hostid in obs:
            if hostid == 'success':
                continue

            host = obs[hostid]
            if 'Sessions' in host:
                ip = str(host['Interface'][0]['IP Address'])
                hostname = host['System info']['Hostname']
                session = host['Sessions'][0]
                access = 'Privileged' if 'Username' in session else 'User'

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

        # Compute required length of vector based on number of hosts
        padding = num_hosts - len(table)
        id_length = math.ceil(math.log2(num_hosts))

        success_value = int(self.success.value) if self.success.value < 2 else -1
        proto_vector = [success_value]
        for row in table:
            # Scanned
            proto_vector.append(int(row[3]))

            # Access
            access = row[4]
            if access == 'None':
                value = [0, 0]
            elif access == 'User':
                value = [1, 0]
            elif access == 'Privileged':
                value = [0, 1]
            else:
                raise ValueError('Table had invalid Access Level')
            proto_vector.extend(value)

        proto_vector.extend(padding * 3 * [-1])

        return np.array(proto_vector)


class BlueTable():
    def __init__(self):
        self.baseline = None
        self.blue_info = {}
        self.last_action = None
        self.info = None

    
    def _process_initial_obs(self, obs):
        obs = obs.copy()
        self.baseline = obs
        del self.baseline['success']
        for hostid in obs:
            if hostid == 'success':
                continue
            host = obs[hostid]
            interface = host['Interface'][0]
            subnet = interface['Subnet']
            ip = str(interface['IP Address'])
            hostname = host['System info']['Hostname']
            self.blue_info[hostname] = [str(subnet),str(ip),hostname, 'None','No']
        return self.blue_info
    
    def observation_change(self,observation, last_action, baseline=False):
        self.last_action = last_action
        obs = observation if type(observation) == dict else observation.data
        obs = deepcopy(observation)
        success = obs['success']

        self._process_last_action()
        anomaly_obs = self._detect_anomalies(obs) if not baseline else obs
        del obs['success']
        # TODO check what info is for baseline
        info = self._process_anomalies(anomaly_obs)
        if baseline:
            for host in info:
                info[host][-2] = 'None'
                info[host][-1] = 'No'
                self.blue_info[host][-1] = 'No'

        self.info = info
        
        return self._create_vector(success)
    
    def _process_last_action(self):
        action = self.last_action
        if action is not None:
            name = action.__class__.__name__
            hostname = action.get_params()['hostname'] if name in ('Restore','Remove') else None

            if name == 'Restore':
                self.blue_info[hostname][-1] = 'No'
            elif name == 'Remove':
                compromised = self.blue_info[hostname][-1]
                if compromised != 'No':
                    self.blue_info[hostname][-1] = 'Unknown'
    
    def _detect_anomalies(self,obs):
        if self.baseline is None:
            raise TypeError('BlueTableWrapper was unable to establish baseline. This usually means the environment was not reset before calling the step method.')

        anomaly_dict = {}

        for hostid,host in obs.items():
            if hostid == 'success':
                continue

            host_baseline = self.baseline[hostid]
            if host == host_baseline:
                continue

            host_anomalies = {}
            if 'Files' in host:
                baseline_files = host_baseline.get('Files',[])
                anomalous_files = []
                for f in host['Files']:
                    if f not in baseline_files:
                        anomalous_files.append(f)
                if anomalous_files:
                    host_anomalies['Files'] = anomalous_files

            if 'Processes' in host:
                baseline_processes = host_baseline.get('Processes',[])
                anomalous_processes = []
                for p in host['Processes']:
                    if p not in baseline_processes:
                        anomalous_processes.append(p)
                if anomalous_processes:
                    host_anomalies['Processes'] = anomalous_processes

            if host_anomalies:
                anomaly_dict[hostid] = host_anomalies

        return anomaly_dict

    def _process_anomalies(self,anomaly_dict):
        info = deepcopy(self.blue_info)
        for hostid, host_anomalies in anomaly_dict.items():
            assert len(host_anomalies) > 0
            if 'Processes' in host_anomalies:
                connection_type = self._interpret_connections(host_anomalies['Processes'])
                info[hostid][-2] = connection_type
                if connection_type == 'Exploit':
                    info[hostid][-1] = 'User'
                    self.blue_info[hostid][-1] = 'User'
            if 'Files' in host_anomalies:
                malware = [f['Density'] >= 0.9 for f in host_anomalies['Files']]
                if any(malware):
                    info[hostid][-1] = 'Privileged'
                    self.blue_info[hostid][-1] = 'Privileged'

        return info
        
    def _interpret_connections(self,activity:list):                
        num_connections = len(activity)

        ports = set([item['Connections'][0]['local_port'] \
            for item in activity if 'Connections' in item])
        port_focus = len(ports)

        remote_ports = set([item['Connections'][0].get('remote_port') \
            for item in activity if 'Connections' in item])
        if None in remote_ports:
            remote_ports.remove(None)

        if num_connections >= 3 and port_focus >=3:
            anomaly = 'Scan'
        elif 4444 in remote_ports:
            anomaly = 'Exploit'
        elif num_connections >= 3 and port_focus == 1:
            anomaly = 'Exploit'
        elif 'Service Name' in activity[0]:
            anomaly = 'None'
        else:
            anomaly = 'Scan'

        return anomaly


    def _create_blue_table(self, success):
        table = PrettyTable([
            'Subnet',
            'IP Address',
            'Hostname',
            'Activity',
            'Compromised'
            ])
        for hostid in self.info:
            table.add_row(self.info[hostid])
        
        table.sortby = 'Hostname'
        table.success = success
        return table

    def _create_vector(self, success):
        table = self._create_blue_table(success)._rows

        proto_vector = []
        for row in table:
            # Activity
            activity = row[3]
            if activity == 'None':
                value = [0,0]
            elif activity == 'Scan':
                value = [1,0]
            elif activity == 'Exploit':
                value = [1,1]
            else:
                raise ValueError('Table had invalid Access Level')
            proto_vector.extend(value)

            # Compromised
            compromised = row[4]
            if compromised == 'No':
                value = [0, 0]
            elif compromised == 'Unknown':
                value = [1, 0]
            elif compromised == 'User':
                value = [0,1]
            elif compromised == 'Privileged':
                value = [1,1]
            else:
                raise ValueError('Table had invalid Access Level')
            proto_vector.extend(value)

        return np.array(proto_vector)