# MATRIX

This repository contains the artifacts for **MATRIX**, presented in our paper **"Enter the MATRIX: Learning & Validating Cybersecurity Strategies in Hybrid Simulation & Emulation Environments"** accepted and to be published at the **IEEE Conference on Dependable and Secure Computing (DSC) 2026**, October 2026.

## Artifact Availability

The repository provides access to the simulation environment, enabling replication of unmodified agent training and evaluation, along with heuristic blue and red agents and resources to train new agents. PPO-based trained agents can be developed and evaluated on the MATRIX platform.

Note on scope:
- Proprietary trained agents are withheld due to intellectual-property restrictions from external organizations.
- Emulated environment evaluations require direct access to hosted enclaves and cannot be made public.
  
---

# Matrix Stable
Matrix Stable includes modified versions of CybORG.
## version_1
'version_1' directory includes modified CybORG v2.1 to enable:
1. Red agent training;
2. Corrected red agent numeric action mapping;
3. Corrected red agent negative numeric actions;
4. Parallelization of training in stable-baselines3.


## RedVisualizationWrapper Addition
We use RedVisualizationWrapper on the CybORG environment to utilize a Flask app which shows the topology and the path that is chosen from the Red agent' perspective. The new Wrapper is added to the Agents/Wrappers folder.
With our RedVisualizationWrapper implementation, we also used Tables.py inside Shared folder, which is basically utils.py that provides RedTable and BlueTable classes.
When the Flask app has started, we open it on a web browser to visualize the graph and go through the games.
Finally, inside examples folder we provide an example of how to use the new wrapper and visualize the graph with Flask and b_line Red agent.

## Random Red agent init Host on every reset
The scope of this task was to be able to change the Attacker Host after every reset of a game. To do this, we made some changes State.py on lines 111-118. 
More specifically, we read Scenario2.yaml as a dictionary and then we replace the host that was originally placed as the Attacker Host with one randomly chosen based on some weights. Additionally, minor changes were made in SimulationController.py and CybORG.py in order to be able to select if we want random host or the predefined one when we initialize the environment. Example of this case is provided in the examples folder.

## RedTableWrapper and Tables changes for ChallengeWrapper Observation
Regarding the ChallengeWrapper Observation, we noticed that the order which every triplet of hosts' information is created by the order that every host is met by the agent. By this logic, the initial host that the Attacker starts at will always be appended at the observation first, not depending on who the host will be. In order to avoid this, we set a specific order of the topology's hosts based on the following list:
['User0', 'User1', 'User2', 'User3', 'User4', 'Enterprise0', 'Enterprise1', 'Enterprise2', 'Defender', 'Op_Server0', 'Op_Host0', 'Op_Host1', 'Op_Host2']
The order is maintained using the TrueTableWrapper when using the RedTableWrapper and the action_mapping_dict when using the RedTable. All of those changes were done on the _create_vector function.
