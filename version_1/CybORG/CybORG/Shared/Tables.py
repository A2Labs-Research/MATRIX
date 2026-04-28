from copy import deepcopy
from prettytable import PrettyTable
from CybORG.Shared.Actions import *
import numpy as np
from ipaddress import IPv4Network, IPv4Address
import math
from CybORG.Shared.Actions.ConcreteActions.ExploitAction import ExploitAction

def map_action(numeric_action, action_mapping_dict):
    mapped_action = action_mapping_dict[int(numeric_action)]
    action = numeric_to_cyborg_action(mapped_action)
    return action


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


class BlueTable():
    def __init__(self, init_obs, last_action = None):
        self.baseline = None
        self.blue_info = {}
        self.last_action = last_action
        self.info = None
        self._process_initial_obs(init_obs)
        self.observation_change(init_obs, last_action = last_action, baseline=True)


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





class RedTable():
    def __init__(self, action_mapping=None):
        self.red_info = {}
        self.known_subnets = set()
        self.step_counter = -1
        self.id_tracker = -1
        self.success = None
        self.last_action = None
        self.action_mapping = action_mapping
    
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
                if ip is not None:
                    self.red_info[ip][3] = True
                    
        elif name == 'ExploitRemoteService' or isinstance(action, ExploitAction):
            try:
                self._add_ips(obs)
            except:
                pass
            self._process_exploit(obs)
        elif name == 'PrivilegeEscalate':
            try:
                self._add_ips(obs)
            except:
                pass
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
                if 'System info' in host.keys():
                    hostname = host['System info']['Hostname']
                else:
                    hostname = hostid
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

        # Compute required length of vector based on number of hosts
        padding = num_hosts - len(table)
        id_length = math.ceil(math.log2(num_hosts))

        success_value = int(self.success.value) if self.success.value < 2 else -1
        proto_vector = [success_value]

        # Follow specific order using action_mapping
        if self.action_mapping:
            # Get action_mapping to match IPs with Subnets and Hostnames
            true_table = self.get_table_from_action_mapping()
            sort_hosts = ['User0', 'User1', 'User2', 'User3', 'User4', 'Enterprise0', 'Enterprise1', 'Enterprise2', 'Defender', 'Op_Server0', 'Op_Host0', 'Op_Host1', 'Op_Host2']
            true_table = [y for x in sort_hosts for y in true_table if y[2] == x]
            
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
        # Base logic with no specific order
        else:
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
    

    def get_table_from_action_mapping(self):
        true_table = []
        for k, v in self.action_mapping.items():
            if k != 'status':
                if v['name'] == 'DiscoverNetworkServices':
                    true_table.append([v['subnet'], v['ip_address'], v['hostname']])
        
        return true_table
