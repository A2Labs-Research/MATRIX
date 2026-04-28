from CybORG.Shared import Observation
from CybORG.Shared.Actions import Action
import random


class GreenConsumeService(Action):
    def __init__(self, session: int, agent: str):
        super().__init__()
        self.agent = agent
        self.session = session
        self.targets = [('Front', 'WebFrontService'), ('Auth', 'AuthService'), ('Database', 'DBService')]

    def sim_execute(self, state) -> Observation:
        for host_suffix, target_service in self.targets:
            # Check if the green agent has an active session on the target host
            # Otherwise, return observation False.
            hostname = None
            for session_info in state.sessions[self.agent].values():
                if host_suffix in session_info.host:
                    hostname = session_info.host
                    break
            if not hostname:
                return Observation(success=False)

            # Check if the service exists and is active.
            # If a condition is not met, return false.
            target_host = state.hosts[hostname]
            service_dict = target_host.services.get(target_service, None)
            if service_dict is None or not service_dict.get('active', False):
                return Observation(success=False)
        obs = Observation(success=True)
        user_list = []
        app_front_target = ""
        for key in state.hosts.keys():
            if "user" in key.lower() or "subnet_0" in key.lower():
                user_list.append(key)
            if "front" in key.lower():
                app_front_target = key
        users_attempting_connection = random.randint(0, len(user_list))
        #print(len(user_list), users_attempting_connection)
        temp_users = random.sample(user_list, users_attempting_connection)
        # print(f"Users that are going to consume APP service are {temp_users}")

        for temp_user in temp_users:
            target_ip = state.hosts[app_front_target].interfaces[1].ip_address
            temp_ip = state.hosts[temp_user].interfaces[1].ip_address
            roll_high_port = random.randint(10000,50000)              # high port for user 
            state.hosts[app_front_target].events['NetworkConnections'].append({'local_address': target_ip,
                                                                                'local_port': 80,
                                                                                'remote_address': temp_ip,
                                                                                'remote_port':roll_high_port})
            state.hosts[temp_user].events['NetworkConnections'].append({'local_address': temp_ip,
                                                                                'local_port': roll_high_port,
                                                                                'remote_address': target_ip,
                                                                                'remote_port': 80})
            obs.add_process(hostid=app_front_target,
                            local_address=target_ip,
                            remote_address=str(temp_ip),
                            local_port=80,
                            remote_port=roll_high_port,
                            process_type='produce_service')
            
            obs.add_process(hostid=temp_user,
                            local_address=str(temp_ip),
                            remote_address=target_ip,
                            local_port=roll_high_port,
                            remote_port=80,
                            process_type='consume_service')
        return obs

    def __str__(self):
        return f"{self.__class__.__name__}"
