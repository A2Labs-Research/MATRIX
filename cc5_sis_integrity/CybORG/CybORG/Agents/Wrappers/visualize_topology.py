import random
from CybORG import CybORG
from CybORG.Agents import BlueMonitorAgent, B_lineAgent
from CybORG.Agents.Wrappers import ChallengeWrapper, TrueTableWrapper, EnumActionWrapper2, RedVisualizationWrapper
import gymnasium as gym
import inspect
from pprint import pprint
import sys
import warnings
from flask import Flask, render_template
import yaml
sys.modules["gym"] = gym
warnings.filterwarnings("ignore")
PATH = str(inspect.getfile(CybORG))

app = Flask(__name__)

nodes = []
links = []

@app.route("/", methods = ['GET','POST'])
def index():
    return render_template('simple_viz_topology.html')

@app.get('/api/reset')
def get_reset():
    global STEP, GAME
    STEP = 0
    GAME = 1
    print(nodes)
    print(links)
    return {"game": GAME, "step": STEP, "nodes": nodes, "links": links, "action": None}

if __name__ == '__main__':
    
    PATH = str(inspect.getfile(CybORG))[:-10] + '/Shared/Scenarios/random_scenario.yaml'

    with open(PATH, 'r') as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)

    info = {}
    for subnet in data['Subnets'].keys():
        info[subnet] = []
        for host in data['Subnets'][subnet]['Hosts']:
            info[subnet].append(host)

    for subnet, hosts in info.items():
        nodes.append({"id": subnet})
        for host in hosts:
            nodes.append({"id":host})
            links.append({"source":subnet, "target":host})
    lista = list(info.keys())
    for i in range(len(lista[1:])):
         links.append({"source":lista[i], "target":lista[i+1]})

    app.run(port=8889,debug=True)

   

    