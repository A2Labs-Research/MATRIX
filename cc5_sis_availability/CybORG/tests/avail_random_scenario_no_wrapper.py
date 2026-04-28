###########################################################################
# Scenario: Random                                                        #
# Blue agent: BlueMonitorAgent/BlueReactRemoveAgent/BlueReactRestoreAgent #
# Red agent: RedMeanderAgent/BLineAgent                                   #
# Random init: True/False                                                 #
# Wrapped: No                                                             #
###########################################################################

from CybORG import CybORG
from CybORG.Agents import BlueReactRemoveAgent, BlueReactRestoreAgent, BlueMonitorAgent, GreenConsumeAgent, RedMeanderAgent_SIS_random, B_lineAgent_SIS_random
from CybORG.Agents.Wrappers import TrueTableWrapper
import gymnasium as gym
import numpy as np
import sys
import warnings
import random
from rich import print


sys.modules["gym"] = gym
warnings.filterwarnings("ignore")

if __name__ == "__main__":
    #### SETTINGS ####
    # 1. Choose blue agent:
    blue_agent = BlueMonitorAgent
    # blue_agent = BlueReactRemoveAgent
    # blue_agent = BlueReactRestoreAgent

    # 2. Choose red agent:
    # red_agent = RedMeanderAgent_SIS_random
    red_agent = B_lineAgent_SIS_random

    # 3. Game duration:
    steps = 30

    # 4. Randomness:
    random_topology = True
    random_red_init = True
    topology_seed = 15
    env_seed = 0

    cyborg = CybORG(None, 'sim', agents={'Red': red_agent, 'Blue': blue_agent, 'Green': GreenConsumeAgent}, random_red_init=random_red_init, random_topologies=random_topology, seed = topology_seed)

    cyborg.set_seed(env_seed)
    results = cyborg.reset()

    true_table = TrueTableWrapper(cyborg)
    table = true_table.get_agent_state('True')
    print(table)

    print(f'\n\n------------------- Game with topology seed {topology_seed} and env seed {env_seed} -------------------')
    for counter in range(steps):
        observation = results.observation
        results = cyborg.step()
        done, info = results.done, results.info
        
        print(f'\n+++++++++++++++++++ Step {counter} +++++++++++++++++++')
        print("--- Actions --- \n")
        print(f"Blue: {cyborg.get_last_action('Blue')}")
        print(f"Red: {cyborg.get_last_action('Red')}")
        print(f"Green: {cyborg.get_last_action('Green')}")

        print("--- Rewards --- \n")
        rewards = cyborg.get_rewards()
        print(f"Blue: {rewards['Blue']}")
        print(f"Red: {rewards['Red']}")       

        print("\n--- Observation Blue ---")
        print(cyborg.get_observation(agent='Blue'))
        print("\n--- Observation Red ---")
        print(cyborg.get_observation(agent='Red'))
        print("\n--- Observation Green ---")
        print(cyborg.get_observation(agent='Green'))


        print((46*"-") + '\n\n\n')

