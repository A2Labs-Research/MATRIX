from CybORG.Shared import Observation
from CybORG.Shared.Actions.ConcreteActions.ConcreteAction import ConcreteAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Process import Process
from CybORG.Simulator.State import State


class StopProcess(ConcreteAction):
    def __init__(self, session: int, agent: str, target_session: int, pid: int):
        super(StopProcess, self).__init__(session, agent)
        self.pid = pid
        self.target_session = target_session

    def sim_execute(self, state: State) -> Observation:
        obs = Observation()
        if self.session not in state.sessions[self.agent] or self.target_session not in state.sessions[self.agent]:
            obs.set_success(False)
            return obs
        target_host: Host = state.hosts[state.sessions[self.agent][self.target_session].host]
        session = state.sessions[self.agent][self.session]
        target_session = state.sessions[self.agent][self.target_session]

        if not session.active or not target_session.active:
            obs.set_success(False)
            return obs
        proc = target_host.get_process(self.pid)
        if proc is not None:
            success = self.kill_process(state, target_host, proc)
            obs.set_success(success=success)
        else:
            obs.set_success(False)
        return obs

    def kill_process(self, state: State, host: Host, process: Process):
        # Remove the suspicious process from the host 
        if process.user.lower() not in ["system", "root"]:
            host.processes.remove(process)
        if process.pid in [i['process'] for i in host.services.values()]:
            process.pid = None
            host.add_process(**process.__dict__)
            service = True
        else:
            service = False


        # Check if the red agent has a session on the target host and has non privileged access.
        # If the access is privileged, then the remove action should fail and the session will not be removed.  
        # If the access is non privileged, remove the session from the host and from the state.
        agent, session = state.get_session_from_pid(host.hostname, pid=process.pid)
        if session is not None:
            red_session = state.sessions[agent][session]
            if red_session.username == 'root' or red_session.username == 'SYSTEM':
                return False
            else:
                host.sessions[agent].remove(session)
                state.sessions[agent].pop(session)
                if service:
                    session_reloaded = state.add_session(host=host.hostname, user=session.user,
                                                        session_type=session.session_type, agent=session.agent,
                                                        parent=session.parent, timeout=session.timeout)
                return True
        else:
            return True
