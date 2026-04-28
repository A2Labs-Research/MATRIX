import numpy as np
from gym import spaces, Env
from typing import Union, List, Any
from prettytable import PrettyTable
from pprint import pprint
import requests
import time
from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
from CybORG.Agents.Wrappers.BaseWrapper import BaseWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Shared.Tables import RedTable, BlueTable
from flask import Flask, render_template
from multiprocessing import Process

# Flask init and global variables
app = Flask(__name__)
nodes, links = [], []
graph_info = {}
STEP = 0
GAME = 0
MAX_STEPS = 100
MAX_GAMES = 10

# Index 
@app.route("/", methods = ['GET','POST'])
def index():
    return render_template('simple_viz.html')

# Reset Button
@app.get('/api/reset')
def get_reset():
    global STEP, GAME
    STEP = 0
    GAME = 1
    return {"game": GAME, "step": STEP, "nodes": {}, "links": {}, "action": None}

# Next Game Button
@app.get('/api/next_game')
def get_next_game():
    global STEP, GAME
    STEP = 0
    if GAME + 1 > MAX_GAMES:
        GAME = GAME
    else:
        GAME = GAME + 1
    return {"game": GAME, "step": STEP, "nodes": graph_info[GAME][STEP][0], "links": graph_info[GAME][STEP][1], "action": graph_info[GAME][STEP][2]}

# Previous Game Button
@app.get('/api/previous_game')
def get_previous_game():
    global STEP, GAME
    STEP = 0
    if GAME - 1 < 1:
        GAME = GAME
    else:
        GAME = GAME - 1
    return {"game": GAME, "step": STEP, "nodes": graph_info[GAME][STEP][0], "links": graph_info[GAME][STEP][1], "action": graph_info[GAME][STEP][2]}
    
# Next Step Button
@app.get('/api/next_step')
def get_next_step():
    global STEP
    if STEP + 1 > MAX_STEPS:
        STEP = STEP
    else:
        STEP = STEP + 1
    return {"game": GAME, "step": STEP, "nodes": graph_info[GAME][STEP][0], "links": graph_info[GAME][STEP][1], "action": graph_info[GAME][STEP][2]}

# Previous Step Button
@app.get('/api/previous_step')
def get_previous_step():
    global STEP
    if STEP - 1 < 1:
        STEP = STEP
    else:
        STEP = STEP - 1
    return {"game": GAME, "step": STEP, "nodes": graph_info[GAME][STEP][0], "links": graph_info[GAME][STEP][1], "action": graph_info[GAME][STEP][2]}



class RedVisualizationWrapper(Env, BaseWrapper):
    def __init__(self, agent_name: str, env, max_steps=100, max_games=10):
        super().__init__(env, agent_name)

        global MAX_GAMES, MAX_STEPS
        MAX_STEPS = max_steps
        MAX_GAMES = max_games

        self.env = env
        self.agent_name = agent_name
        self.table = RedTable()

        # Create action_space and observation space (Temporary solution for self.get_action_space_ = 160)
        self.get_action_space_ = 160
        self.action_space = spaces.Discrete(self.get_action_space_)
        box_len = len(self.table.observation_change(self.env.reset(self.agent_name).observation, last_action=None))
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(box_len,), dtype=np.float32)

        self.observation = self.env.reset(self.agent_name).observation
        self.action = None

        self.path_links = []
        self.source = None
        
    def step(self, action: Union[int, List[int]] = None):
        global STEP
        STEP += 1

        self.action = action
        results = self.env.step(action=self.action, agent=self.agent_name)
        self.observation = results.observation

        # Use observation change from RedTable to transform the observation and update the graph_info
        _ = self.table.observation_change(observation=self.observation.copy(), last_action=self.action)
        graph_info[GAME][STEP] = self.graph_step(self.table.red_info)

        return self.observation, results.reward, results.done, results.info

    def reset(self):
        self.table = RedTable()
        self.source = None
        self.path_links = []
        
        global STEP, GAME
        STEP = 0
        GAME += 1

        results = self.env.reset(agent=self.agent_name)
        self.observation = results.observation

        # Use observation change from RedTable to transform the observation and update the graph_info
        _ = self.table.observation_change(observation=self.observation.copy(), last_action=None)
        self.source = self.table.red_info[list(self.table.red_info.keys())[0]][2]
        if GAME not in graph_info.keys():
            graph_info[GAME] = {}
        graph_info[GAME][STEP] = self.graph_step(self.table.red_info)

        return self.observation

    def render(self):
        global STEP, GAME
        STEP = 0
        GAME = 1
        # Run Flask app (use debug=True to update the app while running)
        app.run(port=8889)#, debug=True)

    def get_attr(self,attribute:str):
        return self.env.get_attr(attribute)

    def get_observation(self, agent: str):
        return self.env.get_observation(agent)

    def get_agent_state(self,agent:str):
        return self.get_attr('get_agent_state')(agent)

    def get_action_space(self,agent):
        return self.env.get_action_space(agent)

    def get_last_action(self,agent):
        return self.get_attr('get_last_action')(agent)

    def get_ip_map(self):
        return self.get_attr('get_ip_map')()

    def get_rewards(self):
        return self.get_attr('get_rewards')()
        
    def seed(self, seed:int):
        self.env.set_seed(seed)

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self

    # Create and update the graph_info used to build to graph
    def graph_step(self, info):
        nodes, links = [], []

        # Create Subnets
        subnets = list(set([v_[0] for k_, v_ in info.items()]))
        for subnet in subnets:
            subnet_name = subnet if 'UNKNOWN_SUBNET' not in subnet else None
            if subnet_name:
                nodes.append({"id":f"{subnet}", "discovered":None, "privilege":None, "step":STEP, "label":f"<p>{subnet}</p>"})

        # Create Nodes (Hosts)
        for k, v in info.items():
            name = k if 'UNKNOWN_HOST' in v[2] else v[2]
            nodes.append({"id":f"{name}", "discovered":v[3], "privilege":v[4], "step":STEP, "label":f"<p>{v}</p>"})
            if 'UNKNOWN_SUBNET' not in v[0]:
                links.append({"source":f"{name}", "target":v[0], "color":'rgba(0,0,0,1)', 'dashed':True, 'animation':0, 'animation_speed': 0})

        # Red Path (Path that the Red agent follows from init red host to OpServer0)
        if 'PrivilegeEscalate' in str(self.action):
            if hasattr(self.action, 'ip_address'):
                target = self.action.ip_address
            elif hasattr(self.action, 'subnet'):
                target = self.action.subnet
            elif hasattr(self.action, 'hostname'):
                target = self.action.hostname
            self.path_links.append({"source":f"{self.source}", "target":target, "color":'rgba(255,0,0,1)', 'dashed':False, 'animation':1, 'animation_speed': 0.002})
            self.source = str(self.action).split(' ')[-1]
        for pl in self.path_links:
            links.append(pl)

        return [nodes, links, str(self.action)]
