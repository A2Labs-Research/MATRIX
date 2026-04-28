# Copyright DST Group. Licensed under the MIT license.
import copy
import inspect
from ipaddress import IPv4Network
from math import log2
from random import sample, choice
import yaml
import json
import time
import uuid
from pprint import pprint
import numpy as np
import csv
import os
import requests
import pickle
import ast

import sys
# sys.path.insert(1, '/home/native/Dispatcher_new')
# import dispatcher_config
from CybORG.Shared.AgentInterface import AgentInterface
from CybORG import CybORG
from CybORG.Shared.Actions import FindFlag, ShellSleep, SambaUsermapScript, UpgradeToMeterpreter, MSFEternalBlue, GetShell, PingSweep
from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.Enums import FileType, TrinaryEnum
from CybORG.Shared.EnvironmentController import EnvironmentController
from CybORG.Shared.Observation import Observation
from CybORG.Shared.Actions import Action, FindFlag, Monitor
from CybORG.Shared.Actions.Action import Sleep, InvalidAction
from CybORG.Shared.Results import Results
from CybORG.Simulator.State import State
from CybORG.Shared.Actions import *
from CybORG.Simulator.utils_encoder import *


class EmulationController(EnvironmentController):
    """The class that controls the Emulation environment.

    Inherits from Environment Controller then implements emulation-specific functionality.
    Most methods are either disabled or delegate their functionality to the State attribute.
    The main thing this class currently does is parse the scenario file.
    """

    def __init__(self, scenario_filepath: str = None, scenario_mod: dict = None, 
                 agents: dict = None, verbose=True):
        self.state = None
        self.network_configuration = None
        self.game_params = None
        self.emulator_client = None
        self.agent_interfaces = self._create_agents(agents)
        super().__init__(scenario_filepath, scenario_mod=scenario_mod, agents=agents)

    def post_init(self, ip_map: dict, game_params: dict) -> None:
        self.game_params = game_params

    def new_game(self, emu_game_params):
        response_new_game = requests.post(dispatcher_config.restapi_url + "/environments", json=emu_game_params)
        if response_new_game.status_code == 202:
            pass
        else:
            print('New_game call failed')
            error_content = response_new_game.json()
            print(error_content.get("error"), str(response_new_game.status_code))
            return None
        
        print('new_game sent to RestAPI')
        print(response_new_game)

        while True:
            print("Read pipe for new_game")
            with open(str(emu_game_params['client_token']) +"_pipe", 'r') as pipe:
                message = pipe.read()
                if message:
                    print(f"Received message from pipe: \n{message}")
                    print()
                    break

        return response_new_game

    def reset(self, agent=None, emu_game_params=None):
        response_reset = requests.put(dispatcher_config.restapi_url + "/environments/" + str(emu_game_params['client_token']), json=emu_game_params)
        if response_reset.status_code == 202:
            pass
        else:
            print('Reset call failed')
            error_content = response_reset.json()
            print(error_content.get("error"), str(response_reset.status_code))
            return None

        print('reset sent to RestAPI')
        print(response_reset)

        while True:
            print("Read pipe for reset")
            with open(str(emu_game_params['client_token']) +"_pipe", 'r') as pipe:
                message = pipe.read()
                if message:
                    print(f"Received message from pipe: \n{message}")
                    print()
                    break

        self.init_state = pickle.loads(ast.literal_eval(message))
        self.reward = {}
        self.steps = 0
        self.done = False

        for agent_name, agent_object in self.agent_interfaces.items():
            agent_object.reset()
            self.observation[agent_name] = self._filter_obs(self.get_true_state(self.INFO_DICT[agent_name]), agent_name)
            agent_object.set_init_obs(self.observation[agent_name].data, self.init_state)


        # TODO (Check Simulation and Environment Controllers reset())
        # TODO Update agent_object and return observation and action_space

        return Results(observation=self.init_state, action_space=self.agent_interfaces[agent].action_space.get_action_space())

    def step(self, agent: str = None, action: Action = None, skip_valid_action_check: bool = False, emu_game_params=None) -> Results:
        next_observation = {}
        self.action = action

        # TODO (Check EnvironmentController step())
        # TODO Loop to get_action, test if it is valid and update next_observation

        # Get true observation
        true_observation = self._filter_obs(self.get_true_state(self.INFO_DICT["True"])).data

        # Execute Action
        if agent == 'Red':
            print(action)
            next_observation[agent] = self.execute_action(action=self.action, params=emu_game_params, mode='emu')
            next_observation['Blue'] = Observation(None)
            next_observation['Green'] = Observation(None)
            print('Emulation Observation')
            print(next_observation[agent])
            self.done = self.determine_done(next_observation, true_observation, self.action)
            reward = 0 # agent_object.determine_reward(next_observation, true_observation, self.action, self.done)
            self.reward = reward + self.action.cost

            self.observation = next_observation
        elif agent == 'Blue':
            print(action)
            next_observation[agent] = self.execute_action(action=self.action, params=emu_game_params, mode='emu')
            next_observation['Red'] = Observation(None)
            next_observation['Green'] = Observation(None)
            print('Emulation Observation')
            print(next_observation[agent])
            self.done = self.determine_done(next_observation, true_observation, self.action)
            reward = 0 # agent_object.determine_reward(next_observation, true_observation, self.action, self.done)
            self.reward = reward + self.action.cost

            self.observation = next_observation

        # TODO (Check EnvironmentController step())
        # TODO Loop to get reward, done and update agent_object

        # TODO (Check EnvironmentController step())
        # TODO Loop execute Monitor for Blue agent

        # TODO Action space return
        if agent is None:
            result = Results(observation=true_observation, done=self.done)
        else:
            result = Results(observation=self.observation[agent].data, done=self.done, reward=round(self.reward, 1), action=self.action)

        return result


    def pause(self):
        pass

    def execute_action(self, action: Action, params=None, mode=None) -> Observation:
        if mode == 'sim':
            return action.sim_execute(self.state)
        elif mode == 'emu':
            params['action'] = action
            return action.emu_execute(self.state, params)
        else:
            return None

    def restore(self, file: str):
        pass

    def save(self, file: str):
        pass

    def get_true_state(self, info: dict) -> Observation:
        output = self.state.get_true_state(info)
        return output

    def shutdown(self, **kwargs):
        pass

    def _parse_scenario(self, scenario_filepath: str, scenario_mod: dict = None):
        scenario_dict = super()._parse_scenario(
            scenario_filepath, scenario_mod=scenario_mod
        )
        images_file_path = str(inspect.getfile(CybORG))
        images_file_path = images_file_path[:-10] + "/Shared/Scenarios/images/"
        with open(images_file_path + "images.yaml") as fIn:
            images_dict = yaml.load(fIn, Loader=yaml.FullLoader)
        if scenario_dict is not None:
            for hostname, image in scenario_dict["Hosts"].items():
                if "path" in images_dict[image["image"]]:
                    with open(
                        images_file_path + images_dict[image["image"]]["path"] + ".yaml"
                    ) as fIn2:
                        scenario_dict["Hosts"][hostname].update(
                            yaml.load(fIn2, Loader=yaml.FullLoader).pop("Test_Host")
                        )
                    image.pop("image")
                else:
                    scenario_dict["Hosts"][hostname] = copy.deepcopy(
                        images_dict[image["image"]]
                    )
        return scenario_dict

    def _create_environment(self):
        self.state = State(self.scenario)
        self.hostname_ip_map = {h: ip for ip, h in self.state.ip_addresses.items()}
        self.subnet_cidr_map = self.state.subnet_name_to_cidr

    def run_schtasks(self):
        for host in self.hosts:
            host.run_scheduled_tasks(self.step)

    def get_last_observation(self, agent):
        return self.observation[agent]
    
    def get_last_action(self, agent: str) -> Action:
        return self.action

    def _create_agents(self, agent_classes: dict = None) -> dict:
        agents = {}

        for agent_name in self.scenario.agents:
            agent_info = self.scenario.get_agent_info(agent_name)
            if agent_classes is not None and agent_name in agent_classes:
                agent_class = agent_classes[agent_name]
            else:
                agent_class = getattr(sys.modules['CybORG.Agents'], agent_info.agent_type)
            agents[agent_name] = AgentInterface(
                agent_class,
                agent_name,
                agent_info.actions,
                agent_info.reward_calculator_type,
                allowed_subnets=agent_info.allowed_subnets,
                wrappers=agent_info.wrappers,
                scenario=self.scenario
            )
        return agents
