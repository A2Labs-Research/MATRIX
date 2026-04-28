from ipaddress import IPv4Address
import requests
import pickle
import ast

from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ExploitAction import ExploitAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.State import State


class HTTPRFI(ExploitAction):
    def __init__(self, session: int, agent: str, ip_address: IPv4Address, target_session: int):
        super().__init__(session, agent, ip_address, target_session)
        self.exploit_port = 80
        self.exploit_name = 'http'

    def sim_execute(self, state: State) -> Observation:
        return self.sim_exploit(state, self.exploit_port, self.exploit_name)

    def emu_execute(self) -> Observation:
        raise NotImplementedError

    def test_exploit_works(self, target_host: Host, vuln_proc: Process):
        # check if OS and process information is correct for exploit to work
        return "rfi" in vuln_proc.properties

    def __str__(self):
        return f"{self.__class__.__name__} {self.ip_address}"