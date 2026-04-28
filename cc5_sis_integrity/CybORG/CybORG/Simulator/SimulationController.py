# Copyright DST Group. Licensed under the MIT license.
import copy
import inspect
from ipaddress import IPv4Network
from math import log2
from random import sample, choice
import yaml
import os
import csv
import json
import numpy as np

from CybORG import CybORG
from CybORG.Shared.Actions import FindFlag, ShellSleep, SambaUsermapScript, UpgradeToMeterpreter, MSFEternalBlue, GetShell, PingSweep
from CybORG.Shared.Actions.Action import Action
from CybORG.Shared.Enums import FileType, TrinaryEnum
from CybORG.Shared.EnvironmentController import EnvironmentController
from CybORG.Shared.Observation import Observation
from CybORG.Shared.Results import Results
from CybORG.Simulator.State import State
from CybORG.Simulator.utils_encoder import *

UNSUPPORTED_ACTIONS = [InvalidAction]

from CybORG.tpr_fpr import HYPERPARAMS

class SimulationController(EnvironmentController):
    """The class that controls the Simulation environment.

    Inherits from Environment Controller then implements simulation-specific functionality.
    Most methods are either disabled or delegate their functionality to the State attribute.
    The main thing this class currently does is parse the scenario file.
    """
    def __init__(self, scenario_filepath: str = None, scenario_mod: dict = None, agents: dict = None, verbose=True, random_red_init=False, random_topologies=False, seed=None, hp=HYPERPARAMS):
        self.seed = seed
        self.state = None
        self.action_distributions = None
        # self._init_load_distribution_file()
        # self.use_action_distributions = False
        self.random_red_init = random_red_init
        self.random_topologies = random_topologies
        self.hp = hp 
        super().__init__(scenario_filepath, scenario_mod=scenario_mod, agents=agents, random_topologies=random_topologies, hp=hp)

    def post_init(self, use_action_distributions : bool) -> None:
        self.use_action_distributions = use_action_distributions

    def _init_load_distribution_file(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        csv_path = os.path.join(dir_path, 'action_probability_distribution.csv')
        with open(csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            # Create a dictionary where each key is the action and the value is the rest of the row
            self.action_distributions = {row['action']: row for row in reader}

    def get_action_taken_probability(self, action_name: str) -> bool:
        """
        Returns True/False based on the probability of an action being taken
        based on the collected action distribution file off of empirical data.
        """
        prob = self._get_prob_for_action(action_name=action_name)
        return bool(np.random.random() <= prob)
    

    def _get_prob_for_action(self, action_name :str) -> float:
        if action_name in self.action_distributions.keys():
            mean = float(self.action_distributions[action_name]['mean'])
            std = float(self.action_distributions[action_name]['std'])
            return np.random.normal(loc=mean,
                                    scale=std,
                                    size=(1))[0] / 100.0
        else:
            print(f"Warning: No action found under supported distribution for specified action: {action_name}")
        return 0.0

    def reset(self, agent=None):
        self.state.reset()
        self.hostname_ip_map = {h: ip for ip, h in self.state.ip_addresses.items()}
        self.subnet_cidr_map = self.state.subnet_name_to_cidr
        return super(SimulationController, self).reset(agent)

    def pause(self):
        pass

    def execute_action(self, action: Action) -> Observation:
        # if self.use_action_distributions and not isinstance(action, tuple(UNSUPPORTED_ACTIONS)):
        #     json_action = json.loads(action_object_to_dict(action))
        #     success = self.get_action_taken_probability(json_action['Action'])
        #     result = action.sim_execute(self.state)
        #     if not success:
        #         # updating the observation to be empty if it was meant to fail
        #         result = Observation(success=False)
        #     return result
        self.state.detection_rate = self.hp.get_tpr()
        return action.sim_execute(self.state)

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
        scenario_dict = super()._parse_scenario(scenario_filepath, scenario_mod=scenario_mod)
        images_file_path = str(inspect.getfile(CybORG))
        images_file_path = images_file_path[:-10] + '/Shared/Scenarios/simulation_images_based_on_emulation/'
        with open(images_file_path + 'images.yaml') as fIn:
            images_dict = yaml.load(fIn, Loader=yaml.FullLoader)
        if scenario_dict is not None:
            for hostname, image in scenario_dict["Hosts"].items():
                if 'path' in images_dict[image["image"]]:
                    with open(images_file_path + images_dict[image["image"]]['path'] + '.yaml') as fIn2:
                        scenario_dict["Hosts"][hostname].update(
                            yaml.load(fIn2, Loader=yaml.FullLoader).pop('Test_Host'))
                    image.pop('image')
                else:
                    scenario_dict["Hosts"][hostname] = copy.deepcopy(images_dict[image["image"]])
        return scenario_dict

    def _create_environment(self):
        self.state = State(self.scenario, random_red_init=self.random_red_init)
        self.hostname_ip_map = {h: ip for ip, h in self.state.ip_addresses.items()}
        self.subnet_cidr_map = self.state.subnet_name_to_cidr

    def run_schtasks(self):
        for host in self.hosts:
            host.run_scheduled_tasks(self.step)

    def get_last_observation(self, agent):
        return self.observation[agent]
