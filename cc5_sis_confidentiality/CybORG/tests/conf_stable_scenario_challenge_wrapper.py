###########################################################################
# Scenario: Stable                                                        #
# Blue agent: BlueMonitorAgent                                            #
# Red agent: BLineAgent                                                   #
# Random init: True/False                                                 #
# Wrapped: Yes                                                            #
###########################################################################

from CybORG import CybORG
from CybORG.Agents import B_lineAgent_SIS_random
from CybORG.Agents.Wrappers import TrueTableWrapper, ChallengeWrapper, EnumActionWrapper2
import gymnasium as gym
import numpy as np
import sys
import warnings
import random
import inspect
from rich import print

sys.modules["gym"] = gym
warnings.filterwarnings("ignore")

if __name__ == "__main__":
    #### SETTINGS ####
    # 1. Choose red agent:
    red_agent = B_lineAgent_SIS_random

    # 2. Game duration:
    steps = 30

    # 3. Randomness:
    random_topology = False
    random_red_init = True
    env_seed = 0

    # 4. Choose scenario:
    # scenario_name = '/Shared/Scenarios/SIS_Confidentiality_Scenarios/Scenario2_SIS_1.yaml'
    # scenario_name = '/Shared/Scenarios/SIS_Confidentiality_Scenarios/Scenario2_SIS_2.yaml'
    # scenario_name = '/Shared/Scenarios/SIS_Confidentiality_Scenarios/Scenario2_SIS_3.yaml'
    scenario_name = '/Shared/Scenarios/SIS_Confidentiality_Scenarios/Scenario2_SIS_4.yaml'
    # scenario_name = '/Shared/Scenarios/SIS_Confidentiality_Scenarios/Scenario2_SIS_5.yaml'

    scenario_file = str(inspect.getfile(CybORG))[:-10] + scenario_name


    cyborg = CybORG(scenario_file, 'sim', agents={'Red': red_agent}, random_red_init=random_red_init, random_topologies=random_topology)
    env = ChallengeWrapper(env=cyborg, agent_name="Blue", scenario_path=scenario_file, paddings=True)


    env.set_seed(env_seed)
    results = env.reset()

    true_table = TrueTableWrapper(cyborg)
    table = true_table.get_agent_state('True')
    print(table)

    enum_action_wrapper = EnumActionWrapper2(env=cyborg, paddings = True)
    red_action_space = enum_action_wrapper.get_action_space(agent='Red')
    blue_action_space = enum_action_wrapper.get_action_space(agent='Blue')

    print('\n+++++++++++++++++++ Action Space (Red) +++++++++++++++++++')
    for i in range(len(red_action_space)):
        print(i,':', red_action_space[i])

    print('\n+++++++++++++++++++ Action Space (Blue) +++++++++++++++++++')
    for i in range(len(blue_action_space)):
        print(i,':', blue_action_space[i])

    print(f'\n\n------------------- Game with env seed {env_seed} -------------------')
    for counter in range(steps):
        monitor_action = 1 
        observation, reward, done, info = env.step(action=monitor_action)
        
        print(f'\n+++++++++++++++++++ Step {counter} +++++++++++++++++++')
        print("--- Actions --- \n")
        print(f"Blue: {cyborg.get_last_action('Blue')}")
        print(f"Red: {cyborg.get_last_action('Red')}")

        print("--- Rewards --- \n")
        rewards = cyborg.get_rewards()
        print(f"Blue: {rewards['Blue']}")
        print(f"Red: {rewards['Red']}")       

        print("\n--- Observation Blue (Vector) ---")
        print(observation)
        print("\n--- Observation Blue ---")
        print(cyborg.get_observation(agent='Blue'))
        print("\n--- Observation Red ---")
        print(cyborg.get_observation(agent='Red'))


        print((46*"-") + '\n\n\n')
