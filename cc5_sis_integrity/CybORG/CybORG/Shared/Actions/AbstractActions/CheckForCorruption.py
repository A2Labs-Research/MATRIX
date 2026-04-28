from random import choice
import inspect
from CybORG import CybORG
from bs4 import BeautifulSoup
import json

from CybORG.Shared import Observation
from .Monitor import Monitor
from CybORG.Shared.Actions import Action
from CybORG.Shared.Actions.ConcreteActions.RestoreContentFromBackup import RestoreContentFromBackup
from CybORG.Simulator.Session import VelociraptorServer
from CybORG.Shared.Actions.AbstractActions import Monitor


def check_front_page(uuid):
    front_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/' + uuid + '/front.html'
    front_initial_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/initial/front.html'

    with open(front_path, "r") as file:
        soup = BeautifulSoup(file, "html.parser")
    with open(front_initial_path, "r") as file_init:
        soup_init = BeautifulSoup(file_init, "html.parser")
    
    element = soup.find(id='para')
    element_init = soup_init.find(id='para')
    if element == element_init:
        return False
    else:
        return True

def check_db(uuid):
    db_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/' + uuid + '/auth.json'
    db_initial_path = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/services/' + uuid + '/initial/auth.json'

    with open(db_path, "r") as file:
        data = json.load(file)
    with open(db_initial_path, "r") as file_init:
        data_initial = json.load(file_init)

    if data == data_initial:
        return False
    else:
        return True
        
class CheckForCorruption(Action):
    def __init__(self, session: int, agent: str):
        super().__init__()
        self.agent = agent
        self.session = session
    
    def sim_execute(self, state) -> Observation:
        obs = Observation(False)
        session: VelociraptorServer = state.sessions[self.agent][self.session]
        for child in session.children.values():
            if 'front' in child.host.lower():
                result = check_front_page(state.game_uuid)
                if result:
                    state.hosts[child.host].defaced_front_status = True
                    #state.hosts[app_front_target].events['DefaceFront'].append(True)
                    obs.add_system_info(hostid=child.host, defaced_status=True, **state.hosts[child.host].get_state())
                    obs.set_success(True)                    
            if 'database' in child.host.lower():
                result = check_db(state.game_uuid)
                if result:
                    state.hosts[child.host].defaced_auth_status = True
                    obs.add_system_info(hostid=child.host, defaced_status=True, **state.hosts[child.host].get_state())
                    obs.set_success(True)                    
                
        return obs

    def __str__(self):
        return f"{self.__class__.__name__}"
