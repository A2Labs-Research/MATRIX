from CybORG import CybORG
from CybORG.Agents import BlueMonitorAgent
from CybORG.Agents.Wrappers import TrueTableWrapper, EnumActionWrapper2, RedVisualizationWrapper
import gymnasium as gym
import inspect
from pprint import pprint
import sys
import warnings
sys.modules["gym"] = gym
warnings.filterwarnings("ignore")


if __name__ == '__main__':
    max_games = 10
    max_steps = 3

    # CybORG init
    PATH = str(inspect.getfile(CybORG))
    PATH = PATH[:-10] + '/Shared/Scenarios/Scenario2.yaml'
    env = CybORG(PATH, 'sim', agents={'Blue': BlueMonitorAgent}, random_red_init=True)  # random_red_init=True to enable random red init on every reset
    vis_env = RedVisualizationWrapper(agent_name='Red', env=env, max_steps=max_steps, max_games=max_games)
    
    vis_env.seed(42)
    results = vis_env.reset()

    # Only do DiscoverRemoteSystems because we don't know on which host we will start
    action_list = [1, 2, 3]

    true_table = TrueTableWrapper(vis_env)
    table = true_table.get_agent_state('True')
    print(table)

    for game in range(max_games):
        # Create action_space to parse numeric action to CybORG actions
        enum_action_wrapper = EnumActionWrapper2(env=vis_env)
        action_space = enum_action_wrapper.get_action_space(agent='Red')

        for action in action_list:
            obs, rew, done, info = vis_env.step(action=action_space[action]) 

            print(f"--- Action --- \n{action} / {action_space[action]}")
            print(f"--- Reward --- \n{rew}")
            print("--- Observation ---")
            pprint(obs)
            print('\n')

        results = vis_env.reset()
        print('----------------- END GAME -----------------')
    
    # Run Flask app (http://127.0.0.1:8889)
    vis_env.render()
