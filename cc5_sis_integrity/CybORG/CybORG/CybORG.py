# Copyright DST Group. Licensed under the MIT license.
import random
from typing import Any
import inspect
import os
import shutil

from CybORG.Shared import Observation, Results, CybORGLogger
from CybORG.Shared.EnvironmentController import EnvironmentController

from CybORG.Simulator.SimulationController import SimulationController
from CybORG.Simulator.EmulationController import EmulationController
from CybORG.Shared.Scenarios.random_topology_SIS import RandomTopologySIS
from CybORG.Shared.Scenarios.services.services_utils import create_init_db, move_files

import uuid
import numpy as np

from CybORG.tpr_fpr import HYPERPARAMS

class CybORG(CybORGLogger):
    """The main interface for the Cyber Operations Research Gym.

    The primary purpose of this class is to provide a unified interface for the CybORG simulation and emulation
    environments. The user chooses which of these modes to run when instantiating the class and CybORG initialises
    the appropriate environment controller.

    This class also provides the external facing API for reinforcement learning agents, before passing these commands
    to the environment controller. The API is intended to closely resemble that of OpenAI Gym.

    Attributes
    ----------
    scenario_file : str
        Path for valid scenario YAML file.
    environment : str, optional
        The environment to use. CybORG currently supports 'sim'
        and 'aws' modes (default='sim').
    env_config : dict, optional
        Configuration keyword arguments for environment controller
        (See relevant Controller class for details), (default=None).
    agents : dict, optional
        Map from agent name to agent interface for all agents to be used internally.
        If None agents will be loaded from description in scenario file (default=None).
    """

    supported_envs = ["sim", "aws"]

    def __init__(
        self,
        scenario_file: str = None,
        environment: str = "sim",
        env_config=None,
        agents: dict = None,
        random_red_init=False,
        random_topologies=False,
        seed=0,
        hyperparams=HYPERPARAMS
    ):
        """Instantiates the CybORG class.

        Parameters
        ----------
        scenario_file : str
            Path for valid scenario YAML file.
        environment : str, optional
            The environment to use. CybORG currently supports 'sim'
            and 'aws' modes (default='sim').
        env_config : dict, optional
            Configuration keyword arguments for environment controller
            (See relevant Controller class for details), (default=None).
        agents : dict, optional
            Map from agent name to agent interface for all agents to be used internally.
            If None agents will be loaded from description in scenario file (default=None).
        """
        self.env = environment
        self.agents = agents
        self.seed = seed
        self.set_seed(seed=self.seed)
        self.random_topologies = random_topologies
        self.scenario_name = str(uuid.uuid4())
        if self.random_topologies:
            r_topology = RandomTopologySIS(seed=self.seed, scenario_name=self.scenario_name)
            self.scenario_file = r_topology.create_topology()
            # print('CybORG INIT new random topology')
        else:
            self.scenario_file = scenario_file
        self._log_info(f"Using scenario file {scenario_file}")
        self.random_red_init = random_red_init

        # create unique uuid for this game
        self.game_uuid = str(uuid.uuid4())
        # print("created game with uuid", self.game_uuid)

        self.hp = hyperparams
        self.environment_controller = self._create_env_controller(env_config, agents)

    def _create_env_controller(self, env_config, agents) -> EnvironmentController:
        """Chooses which Environment Controller to use then instantiates it.

        Parameters
        ----------
        """
        if self.env == "sim":
            temp_env = SimulationController(self.scenario_file, agents=agents, random_red_init=self.random_red_init, random_topologies=self.random_topologies, seed=self.seed, hp=self.hp)
            temp_env.state.game_uuid = self.game_uuid
            return temp_env
        if self.env == "aws":
            pass
            # if env_config:
            #     return AWSClientController(self.scenario_file, agents=agents, **env_config)
            # else:
            #     return AWSClientController(self.scenario_file, agents=agents)
        if self.env == "emu":
            return EmulationController(self.scenario_file, agents=agents)

        raise NotImplementedError(f"Unsupported environment '{self.env}'. Currently supported " f"environments are: {self.supported_envs}")

    def step(self, agent: str = None, action=None, skip_valid_action_check: bool = False) -> Results:
        """Performs a step in CybORG for the given agent.

        Parameters
        ----------
        agent : str, optional
            the agent to perform step for (default=None)
        action : Action
            the action to perform
        skip_valid_action_check : bool
            a flag to diable the valid action check
        Returns
        -------
        Results
            the result of agent performing the action
        """

        return self.environment_controller.step(agent, action, skip_valid_action_check)

    def start(self, steps: int, log_file=None) -> bool:
        """Start CybORG and run for a specified number of steps.

        Parameters
        ----------
        steps : int
            the number of steps to run for
        log_file : File, optional
            a file to write results to (default=None)

        Returns
        -------
        bool
            whether goal was reached or not
        """
        return self.environment_controller.start(steps, log_file)

    def get_true_state(self, info: dict) -> dict:
        """
        Query the current state.

        Parameters
        ----------
        info : dict
            Dictionary con

        Returns
        -------
        Results
            The information requested.
        """
        return self.environment_controller.get_true_state(info).data

    def get_agent_state(self, agent_name) -> dict:
        """
        Get the initial observation of the specified agent.

        Parameters
        ----------
        agent : str
            The agent to get the initial observation for.
            Set as 'True' to get the true-state.

        Returns
        -------
        dict
            The initial observation of the specified agent.
        """
        return self.environment_controller.get_agent_state(agent_name).data

    def reset(self, agent: str = None) -> Results:
        # print("Cyborg reset called")
        """
        Resets CybORG and gets initial observation and action-space for the specified agent.

        Note
        ----
        This method is a critical part of the OpenAI Gym API.

        Parameters
        ----------
        agent : str, optional
            The agent to get the initial observation for.
            If None will return the initial true-state (default=None).

        Returns
        -------
        Results
            The initial observation and actions of an agent.
        """


        if self.random_topologies:
            r_topology = RandomTopologySIS(seed=self.seed, scenario_name=self.scenario_name)
            self.scenario_file = r_topology.create_topology()
            # print('CybORG RESET new random topology')

        folder_path = str(inspect.getfile(CybORG))[:-10] + "/Shared/Scenarios/services/" + self.game_uuid + "/user_pages"
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")

        create_init_db(self.scenario_file, self.game_uuid)
        move_files(None, self.game_uuid)

        # self.environment_controller.random_init_func(self.scenario_file, agent=agent, agents=self.agents)
        self.environment_controller = self._create_env_controller(None, self.agents)
        sim = self.environment_controller.reset(agent=agent)
        # print("reset env controller")
        for k, v in self.environment_controller.agent_interfaces.items():
            if hasattr(v.agent, "set_env"):
                v.agent.set_env(env=self)

        return sim

    def shutdown(self, **kwargs) -> bool:
        """
        Shuts down the CybORG environment.

        Parameters
        ----------
        **kwargs : dict, optional
            Keyword arguments to pass to the environment controller shutdown
            function. See the shutdown function of the specific environment
            controller used for details.

        Returns
        -------
        bool
            True if cyborg was shutdown without any issues.
        """
        self.environment_controller.shutdown(**kwargs)
        if self.random_topologies:
            os.remove(self.scenario_file)
            topo_dir = os.path.dirname(self.scenario_file)
            service_dir = topo_dir + '/../services/'
            shutil.rmtree(service_dir + self.game_uuid + '/')


    def pause(self):
        """Pauses the environment."""
        self.environment_controller.pause()

    def save(self, filepath: str):
        """
        Saves the CybORG environment to a file.

        Note
        ----
        Not currently supported for all environments.

        Parameters
        ----------
        filepath : str
            Path to file to save environment to.
        """
        self.environment_controller.save(filepath)

    def restore(self, filepath: str):
        """
        Restores the CybORG environment from a file.

        Note
        ----
        Not currently supported for all environments.

        Parameters
        ----------
        filepath : str
            Path to file to restore environment from.
        """
        self.environment_controller.restore(filepath)

    def get_observation(self, agent: str) -> dict:
        """
        Get the last observation for an agent.

        Parameters
        ----------
        agent : str
            Name of the agent to get observation for.

        Returns
        -------
        Observation
            The agent's last observation.
        """
        return self.environment_controller.get_last_observation(agent).data

    def get_action_space(self, agent: str):
        """
        Returns the most recent action space for the specified agent.

        Action spaces may change dynamically as the scenario progresses.

        Parameters
        ----------
        agent : str
            Name of the agent to get action space for.

        Returns
        -------
        dict
            The action space of the specified agent.

        """
        return self.environment_controller.get_action_space(agent)

    def get_observation_space(self, agent: str):
        """
        Returns the most recent observation for the specified agent.

        Parameters
        ----------
        agent : str
            Name of the agent to get observation space for.

        Returns
        -------
        dict
            The observation of the specified agent.

        """
        return self.environment_controller.get_observation_space(agent)

    def get_last_action(self, agent: str):
        """
        Returns the last executed action for the specified agent.

        Parameters
        ----------
        agent : str
            Name of the agent to get last action for.

        Returns
        -------
        Action
            The last action of the specified agent.

        """
        return self.environment_controller.get_last_action(agent)

    def set_seed(self, seed: int):
        """
        Sets a random seed.

        Parameters
        ----------
        seed : int
        """
        random.seed(seed)
        np.random.seed(seed)
        self.seed = seed

    def get_ip_map(self):
        """
        Returns a mapping of hostnames to ip addresses for the current scenario.

        Returns
        -------
        dict
            The ip_map indexed by hostname.

        """
        return self.environment_controller.hostname_ip_map

    def get_rewards(self):
        """
        Returns the rewards for each agent at the last executed step.

        Returns
        -------
        dict
            The rewards indexed by agent name.

        """
        return self.environment_controller.reward

    def get_reward_breakdown(self, agent: str):
        return self.environment_controller.get_reward_breakdown(agent)

    def get_attr(self, attribute: str) -> Any:
        """
        Returns the specified attribute if present.

        Intended to give wrappers access to the base CybORG class.

        Parameters
        ----------
        attribute : str
            Name of the requested attribute.

        Returns
        -------
        Any
            The requested attribute.
        """
        if hasattr(self, attribute):
            return self.__getattribute__(attribute)
        else:
            return None
