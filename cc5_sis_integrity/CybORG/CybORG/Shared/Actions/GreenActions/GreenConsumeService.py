from CybORG import CybORG
from CybORG.Shared import Observation
from CybORG.Shared.Actions import Action
import random
import inspect
from bs4 import BeautifulSoup
import json

class GreenConsumeService(Action):
    def __init__(self, session: int, agent: str):
        super().__init__()
        self.agent = agent
        self.session = session
        self.targets = [('Front', 'WebFrontService'), ('Auth', 'AuthService')]

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
        db_target = ""
        for key in state.hosts.keys():
            if "user" in key.lower() or "subnet_0" in key.lower():
                user_list.append(key)
            if "front" in key.lower():
                app_front_target = key
            if "auth" in key.lower():
                db_target = key
        users_attempting_connection = random.randint(0, len(user_list))
        temp_users = random.sample(user_list, users_attempting_connection)
        defaced_front = []
        defaced_auth = []
        # print(f"Users that are going to consume APP service are {temp_users}")

        for temp_user in temp_users:
            target_front_ip = state.hosts[app_front_target].interfaces[1].ip_address
            target_db_ip = state.hosts[db_target].interfaces[1].ip_address
            temp_ip = state.hosts[temp_user].interfaces[1].ip_address
            roll_high_port = random.randint(10000,50000)              # high port for user (front)
            roll_high_port_2 = random.randint(10000,50000)              # high port for user (db)
            if roll_high_port_2 == roll_high_port:
                roll_high_port_2 += 1
            
            # Front
            state.hosts[app_front_target].events['NetworkConnections'].append({'local_address': target_front_ip, 'local_port': 80,
                                                                                'remote_address': temp_ip, 'remote_port':roll_high_port})
            state.hosts[temp_user].events['NetworkConnections'].append({'local_address': temp_ip, 'local_port': roll_high_port,
                                                                        'remote_address': target_front_ip, 'remote_port': 80})
            
            obs.add_process(hostid=app_front_target, local_address=target_front_ip, remote_address=str(temp_ip), 
                            local_port=80, remote_port=roll_high_port, process_type='produce_service')
            
            obs.add_process(hostid=temp_user, local_address=str(temp_ip), remote_address=target_front_ip,
                            local_port=roll_high_port, remote_port=80, process_type='consume_service')

            # DB
            state.hosts[db_target].events['NetworkConnections'].append({'local_address': target_db_ip, 'local_port': 9090,
                                                                        'remote_address': temp_ip, 'remote_port':roll_high_port_2})
            state.hosts[temp_user].events['NetworkConnections'].append({'local_address': temp_ip, 'local_port': roll_high_port_2,
                                                                        'remote_address': target_db_ip, 'remote_port': 9090})
            
            obs.add_process(hostid=db_target, local_address=target_db_ip, remote_address=str(temp_ip), 
                            local_port=9090, remote_port=roll_high_port_2, process_type='produce_service')
            
            obs.add_process(hostid=temp_user, local_address=str(temp_ip), remote_address=target_db_ip,
                            local_port=roll_high_port_2, remote_port=9090, process_type='consume_service')

            result_f = self.check_front_page(temp_user, state)
            result_db = self.check_db(temp_user, state)

            if result_f and result_db:
                defaced_front.append({'green_user': temp_user, 'message': 'sis_front_defaced and sis_auth_corrupted'})                
                defaced_auth.append({'green_user': temp_user, 'message': 'sis_front_defaced and sis_auth_corrupted'})
            elif result_db:
                defaced_auth.append({'green_user': temp_user, 'message': 'sis_auth_corrupted'})
            elif result_f:
                defaced_front.append({'green_user': temp_user, 'message': 'sis_front_defaced'})                
            else:
                pass

        if defaced_front != []:
            state.defaced_front(app_front_target, defaced_front)
            state.hosts[app_front_target].events['DefaceFront'].append(True)
            obs.add_key_value('user_complaint', defaced_front)
        if defaced_auth != []:
            state.defaced_auth(db_target, defaced_auth)
            state.hosts[db_target].events['DefaceAuth'].append(True)
            obs.add_key_value('user_complaint', defaced_auth)

        return obs

    def check_front_page(self, name, state):
        front_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/' + state.game_uuid + '/front.html'
        front_initial_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/initial/front.html'
        with open(front_path, "r") as file:
            soup = BeautifulSoup(file, "html.parser")
        with open(front_initial_path, "r") as file_init:
            soup_init = BeautifulSoup(file_init, "html.parser")
        
        element = soup.find(id='para')
        element_init = soup_init.find(id='para')
        if element == element_init:
            #print('Front page is OK!')
            return False
        else:
            # print('Defaced Front page!')
            return True
    
    def check_db(self, username, state):
        user_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/' + state.game_uuid + '/user_pages/' + username + '.html'
                
        with open(user_path, "r") as file:
            soup = BeautifulSoup(file, "html.parser")

        element = soup.find(id='para1').text.strip()
        if element == username:
            #print('Database is OK!')
            return False
        else:
            # print('Defaced Authentication!')
            return True

    def parse_and_normalize(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        soup = BeautifulSoup(content, 'html.parser')
        
        for tag in soup(['script', 'style']):
            tag.decompose()
        
        return soup.prettify()
    
    def load_and_normalize_json(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    
    def __str__(self):
        return f"{self.__class__.__name__}"
