 

"""
pertaining to the Juicy Potato permissions escalation action
"""
# pylint: disable=invalid-name
from typing import Tuple

from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.EscalateAction import EscalateAction
from CybORG.Shared.Enums import OperatingSystemType
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.State import State


class JuicyPotato(EscalateAction):
    """
    Implements the Juicy Potato permissions escalation action
    """
    def sim_execute(self, state: State) -> Observation:
        return self.sim_escalate(state, "SYSTEM")

    def emu_execute(self) -> Observation:
        raise NotImplementedError

    def test_exploit_works(self, target_host: Host) ->\
            Tuple[bool, Tuple[Process, ...]]:
        # the exact patches and OS distributions are described here:
        return target_host.os_type == OperatingSystemType.WINDOWS, ()
