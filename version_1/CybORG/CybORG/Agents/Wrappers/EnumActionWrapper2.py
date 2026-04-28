import copy
import inspect, pprint
from typing import Union, List
from CybORG.Shared.Actions.Action import InvalidAction
from CybORG.Agents.SimpleAgents import BaseAgent
from CybORG.Agents.Wrappers import BaseWrapper
from CybORG.Shared import Results, ActionSpace

class EnumActionWrapper2(BaseWrapper):
    def __init__(self, env: Union[type, BaseWrapper] = None, agent: BaseAgent = None):
        super().__init__(env, agent)
        self.possible_actions = None
        self.action_signature = {}
        self.get_action_space('Red')
    def find_max_target_session(self,possible_actions:list)->int:
        """This function aims to find the max target session available in possible actions
        Args:
            possible_actions (list): all possible
        Returns:
            int: max target session available
        """
        # Assuming ActionSpace.MAX_SESSIONS is a predefined constant
        max_target_session_present:int = ActionSpace.MAX_SESSIONS
        for action in possible_actions:
            try:
                temp_target_session = action.target_session
                if temp_target_session > max_target_session_present:
                    max_target_session_present = temp_target_session
            except Exception as e:
                # Exception ignored, continue with next action
                pass
        return max_target_session_present
    def organize_actions_based_on_session(self, possible_actions:list, max_target_session_present:int)->list:
        """This function aims to order the new possible actions without touching the initial ordering till 888 (for MAX_SESSIONS = 8)
        Args:
            possible_actions (list): list of all possible actions
            max_target_session_present (int): max targets session
        Returns:
            list: newly ordered list
        """
        if possible_actions is None:
            possible_actions = []
        old_action_list:list = []
        new_action_list:list = []
        if max_target_session_present == ActionSpace.MAX_SESSIONS - 1:
            self.possible_actions = possible_actions
        else:
            for action in possible_actions:
                try:
                    temp_target_session = action.target_session
                    if temp_target_session < ActionSpace.MAX_SESSIONS:
                        old_action_list.append(action)
                    else:
                        new_action_list.append(action)
                except Exception:
                    old_action_list.append(action)
            for i in range(ActionSpace.MAX_SESSIONS, max_target_session_present + 1):
                for action in new_action_list:
                    if action.target_session == i:
                        old_action_list.append(action)
            self.possible_actions = old_action_list
        return self.possible_actions
    def step(self, agent=None, action: int = None, flag: Union[bool, List[bool]] = None) -> Results:
        if action is not None:
            action = self.possible_actions[action]
        # InvalidAction check 1
            if isinstance(flag, bool):
                # flag is a single boolean
                if flag is False:
                    action = InvalidAction(action)
            elif isinstance(flag, list):
                # flag is a list of booleans
                action = [InvalidAction for flags in flag if flags is False]
        return super().step(agent, action)
    def action_space_change(self, action_space: dict) -> list:
        assert type(action_space) is dict, \
            f"Wrapper required a dictionary action space. " \
            f"Please check that the wrappers below the ReduceActionSpaceWrapper return the action space as a dict "
        possible_actions = []
        temp = {}
        params = ['action']
        # for action in action_space['action']:
        for i, action in enumerate(action_space['action']):
            if action not in self.action_signature:
                self.action_signature[action] = inspect.signature(action).parameters
            param_list = [{}]
            for p in self.action_signature[action]:
                if p == 'priority':
                    continue
                temp[p] = []
                if p not in params:
                    params.append(p)
                if len(action_space[p]) == 1:
                    for p_dict in param_list:
                        p_dict[p] = list(action_space[p].keys())[0]
                else:
                    new_param_list = []
                    for p_dict in param_list:
                        for key, val in action_space[p].items():
                            #print('Key is', key, '  Val is', val)
                            p_dict[p] = key
                            new_param_list.append({key: value for key, value in p_dict.items()})
                    param_list = new_param_list
            for p_dict in param_list:
                possible_actions.append(action(**p_dict))
        #self.possible_actions = possible_actions
        max_target_session_present = self.find_max_target_session(possible_actions)
        self.possible_actions = self.organize_actions_based_on_session(possible_actions, max_target_session_present)
        return self.possible_actions