from CybORG import CybORG
from CybORG.Agents import BlueMonitorAgent, B_lineAgent
from CybORG.Agents.Wrappers import TrueTableWrapper, RedVisualizationWrapper
import gymnasium as gym
import inspect
from pprint import pprint
import sys
import warnings
sys.modules["gym"] = gym
warnings.filterwarnings("ignore")


if __name__ == '__main__':
    max_games = 4
    max_steps = 15

    # CybORG init
    PATH = str(inspect.getfile(CybORG))
    PATH = PATH[:-10] + '/Shared/Scenarios/Scenario2.yaml'
    env = CybORG(PATH, 'sim', agents={'Blue': BlueMonitorAgent})
    vis_env = RedVisualizationWrapper(agent_name='Red', env=env, max_steps=max_steps, max_games=max_games)

    vis_env.seed(42)
    action_space = env.reset().action_space
    results = vis_env.reset()

    true_table = TrueTableWrapper(vis_env)
    table = true_table.get_agent_state('True')
    print(table)

    for game in range(max_games):
        red_agent = B_lineAgent()
        obs = results
        for _ in range(max_steps):
            action = red_agent.get_action(observation=obs, action_space=action_space)
            obs, rew, done, info = vis_env.step(action=action) 

            print(f"--- Action --- \n{action}")
            print(f"--- Reward --- \n{rew}")
            print("--- Observation ---")
            pprint(obs)
            print('\n')

        results = vis_env.reset()
        print('----------------- END GAME -----------------')

    # Run Flask app (http://127.0.0.1:8889)
    vis_env.render()