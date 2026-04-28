 
from ipaddress import IPv4Address
from typing import Optional
import requests
import pickle
import ast
import sys
from random import random

from CybORG.Shared.Actions.ConcreteActions.ExploitAction import ExploitAction
from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import lo, lo_subnet
from CybORG.Shared.Enums import SessionType, ProcessType, OperatingSystemType, DecoyType
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.Host import Host
from CybORG.Simulator.State import State
from CybORG.Simulator.Process import Process
from CybORG.Shared.Actions.AbstractActions.PrivilegeEscalate import PrivilegeEscalate


class SSHBruteForce(ExploitAction):
    def __init__(self, ip_address: IPv4Address, agent: str, session: int, target_session: int):
        super().__init__(session=session, agent=agent, ip_address=ip_address,
                target_session=target_session)
        self.ip_address = ip_address
        self.target_session = target_session
        self.exploit_port = 22
        self.exploit_name = 'sshd'

    # def test_exploit_works(self, target_host: Host, vuln_proc: Process):        
    #     # make sure the Haraka version < 2.8.9        
    #     return bool(True)
    
    # def sim_execute(self, state: State) -> Observation:
    #     return self.sim_exploit(state, 22, 'ssh')

    def sim_execute(self, state: State):
        self.state = state
        length_of_wordlist = 10
        obs = Observation()
        if self.session not in state.sessions[self.agent]:
            obs.set_success(False)
            return obs
        from_host: Host = state.hosts[state.sessions['Red'][self.session].host]
        session = state.sessions['Red'][self.session]

        if not session.active:
            obs.set_success(False)
            return obs

        # determine which ports can communicate between which subnets
        originating_ip_address = None
        if self.ip_address == lo:
            target_host: Host = from_host
            originating_ip_address = self.ip_address
        else:
            target_host: Host = state.hosts[state.ip_addresses[self.ip_address]]
            ports = self.check_routable(
                [state.subnets[i.subnet] for i in from_host.interfaces if i.ip_address != lo],
                [s for s in state.subnets.values() if self.ip_address in s.cidr])
            if ports is None or (self.exploit_port not in ports and 'all' not in ports):
                obs.set_success(False)
                return obs
            from_subnet, to_subnet = ports[self.exploit_port] if self.exploit_port in ports else ports['all']
            # calculate the originating ip address
            for i in from_host.interfaces:
                if i.ip_address != lo:
                    if i.subnet == from_subnet:
                        originating_ip_address = i.ip_address

        # find out if smb is open
        vuln_proc: Optional[Process] = None
        for proc in target_host.processes:
            if proc.process_type == ProcessType.SSH:
                for conn in proc.connections:
                    if 'local_port' in conn and conn['local_port'] == self.exploit_port:
                        vuln_proc = proc
                        break
                if vuln_proc is not None:
                    break

        if vuln_proc is None:
            obs.set_success(False)
            return obs
        obs.add_process(hostid=str(self.ip_address), local_address=self.ip_address, local_port=self.exploit_port, status="open",
                        process_type='SSH')

        # print('Exploit User:', vuln_proc.user)

        # test if there is a bruteforceable user-pass on the system
        user = None
        for u in target_host.users:
            if u.bruteforceable:
                user = u
                break

        detection_roll = random()
        if detection_roll < state.detection_rate['SSHBruteForce']:
            for i in range(length_of_wordlist):
                target_host.events['NetworkConnections'].append({'remote_address': originating_ip_address,
                                                                'remote_port': from_host.get_ephemeral_port(),
                                                                'local_address': self.ip_address,
                                                                'local_port': self.exploit_port
                                                                })

        if user is not None and not (vuln_proc.decoy_type & DecoyType.EXPLOIT):
            obs.set_success(True)

            new_proc = target_host.add_process(name=self.exploit_name, ppid=vuln_proc.pid, path=vuln_proc.path, user=user.username, process_type="ssh")

            if bool(vuln_proc.decoy_type & DecoyType.SANDBOXING_EXPLOIT):

                new_session = state.add_session(host=target_host.hostname, agent=self.agent,
                                            user=user.username, session_type="ssh", parent=session, process=new_proc.pid,
                                            is_escalate_sandbox=True)
            else:

                new_session = state.add_session(host=target_host.hostname, agent=self.agent,
                                            user=user.username, session_type="ssh", parent=session, process=new_proc.pid)

            remote_port = target_host.get_ephemeral_port()
            new_connection = {"local_port": self.exploit_port,
                              "Application Protocol": "tcp",
                              "remote_address": originating_ip_address,
                              "remote_port": remote_port,
                              "local_address": self.ip_address}
            new_proc.connections.append(new_connection)
            if detection_roll < state.detection_rate['SSHBruteForce']:
                target_host.events['NetworkConnections'].append({'remote_address': originating_ip_address,
                                                                'remote_port': remote_port,
                                                                'local_address': self.ip_address,
                                                                'local_port': self.exploit_port
                                                                })

            remote_port_dict = {'local_port': remote_port,
                                "Application Protocol": "ssh",
                                "local_address": originating_ip_address,
                                "remote_address": self.ip_address,
                                "remote_port": self.exploit_port
                                }
            from_host.get_process(session.pid).connections.append(remote_port_dict)
            obs.add_process(hostid=str(originating_ip_address), local_address=originating_ip_address, remote_address=self.ip_address,
                            local_port=remote_port, remote_port=self.exploit_port)
            obs.add_process(hostid=str(self.ip_address), local_address=self.ip_address, remote_address=originating_ip_address,
                            local_port=self.exploit_port, remote_port=remote_port, process_type='ssh')
            obs.add_session_info(hostid=str(self.ip_address), username=user.username, session_id=new_session.ident, session_type="ssh", agent=self.agent)
            obs.add_user_info(hostid=str(self.ip_address), username=user.username, password=user.password, uid=user.uid)

            obs.add_system_info(hostid=str(self.ip_address), hostname=target_host.hostname, os_type=target_host.os_type)
            
            if self.ip_address != lo and obs.data['success'] == True:
                hostname = obs.data[str(self.ip_address)]["System info"]["Hostname"]
                os = obs.data[str(self.ip_address)]["System info"]["OSType"]
                state.sessions[self.agent][self.session].addos(hostname, os)

                # if user.username == 'root' or user.username == 'SYSTEM':
                #     print('ssh: getting on priv esc..')
                #     additional_action = PrivilegeEscalate(session=self.session, agent=self.agent, hostname=hostname)
                #     priv_esc_obs = additional_action.sim_execute(state=state)
                #     obs.combine_obs(priv_esc_obs)
        else:
            obs.set_success(False)
        return obs

    def emu_execute(self) -> Observation:
        raise NotImplementedError

    def __str__(self):
        return f"{self.__class__.__name__} {self.ip_address}"