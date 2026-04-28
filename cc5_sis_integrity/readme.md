# AI2CybCage

This repository contains the updated version of CybORG Cage-Challenge-2 from https://github.com/cage-challenge/cage-challenge-2. Here, we provide a lightweight version of CybORG containing training samples and a completed requirements.txt file.


## Cyber Operations Research Gym (CybORG)

A cyber security research environment for training and development of security human and autonomous agents. Contains a common interface for both emulated, using cloud based virtual machines, and simulated network environments. You can find more information in the [AI2CybCage Review](/Cage%20Challenge%202%20-%20Review.pdf)


## Installation

Install CybORG locally using pip

```
# from the AI2CybCage/CybORG directory
./install.sh

For executable bash run: chmod u+x install.sh

```

## Structure

### Folder Structure

    .
    ├── ...
    ├── CybORG                    
    │   ├── CybORG              
    │   │   ├── Agents
    │   │   │   ├── SimpleAgents        # Predefined Agents
    │   │   │   ├── Wrappers            # CybORG Wrappers
    │   │   ├── Shared
    │   │   │   ├── Actions             # Abstract and Concrete Actions
    │   │   │   ├── Config              # CybORGConfig class
    │   │   │   ├── Plugins             # CybORG Plugins
    │   │   │   ├── Scenarios           # Scenarios and Images to Run
    │   │   ├── Simulator               # Simulated Observation
    │   │   ├── Train                   # Sample train scripts
    │   │   ├── CybORG.py               # Base CybORG class
    │   ├── Requirements.txt            # Python3.8.17 env requirements
    │   ├── setup.py                    # Run to setup CybORG
    ├── CageChallenge2-Review.pdf       # PDF Review 
    └── ReadMe.md


### Simulation Environment

To utilize a simulated environment, we start by creating the Scenario, a valid YAML file that contains all the information about the Network. 
Then, we instantiate it using the [Cyborg class](CybORG/CybORG/CybORG.py), with parameters the path of the scenario and the type of environment (sim for simulation). 
The [EnvironmentController](CybORG/CybORG/Shared/EnvironmentController.py) contains all the abstract methods for both simulation (SimulationEnvironment.py) and emulation environments.

### Observation

An observation state is created using the State class and then adds information to the [Observation class](CybORG/CybORG/Simulator/State.py) and CybORG/CybORG/Shared/Observation.py accordingly. Both agents use the same observation space.

- Success (TrinaryEnum)
- Hosts
- Interface
- Sessions
- Processes
- SystemInfo
- Files
- Users

### Actions

Cyborg implements an action abstraction, that is the base class describing the concept of an action. Every other concrete action or “type / category” of actions inherits this class.

#### Blue Agent Abstract Actions
- [Monitor](CybORG/CybORG/Shared/Actions/AbstractActions/Monitor.py)
- [Analyze](CybORG/CybORG/Shared/Actions/AbstractActions/Analyse.py)
- [Misinform](CybORG/CybORG/Shared/Actions/AbstractActions/Misinform.py)
- [Remove](CybORG/CybORG/Shared/Actions/AbstractActions/Remove.py)
- [Restore](CybORG/CybORG/Shared/Actions/AbstractActions/Restore.py)

#### Red Agent Abstract Actions
- [DiscoverRemoteSystems](CybORG/CybORG/Shared/Actions/AbstractActions/DiscoverRemoteSystems.py)
- [DiscoverNetworkServices](CybORG/CybORG/Shared/Actions/AbstractActions/DiscoverNetworkServices.py)
- [ExploitRemoteService](CybORG/CybORG/Shared/Actions/AbstractActions/ExploitRemoteService.py)
- [PriviligeEscalate](CybORG/CybORG/Shared/Actions/AbstractActions/PrivilegeEscalate.py)
- [Impact](CybORG/CybORG/Shared/Actions/AbstractActions/Impact.py)

### Scenarios
Scenarios are a main component of Cyborg implementation as it initializes the structure of the network the agent will take actions. Scenarios must be valid YAML files located in /CybORG/CybORG/Shared/Scenarios/.

### Wrappers

- [OpenAIGymWrapper](CybORG/CybORG/Agents/Wrappers/OpenAIGymWrapper.py) - alters the interface to conform to the OpenAI Gym specification.
- [FixedFlatWrapper](CybORG/CybORG/Agents/Wrappers/FixedFlatWrapper.py) - converts the observation from a dictionary format into a fixed size 1-dimensional vector of floats
- [EnumActionWrapper](CybORG/CybORG/Agents/Wrappers/EnumActionWrapper.py) - converts the action space into a single integer
- [IntListToActionWrapper](CybORG/CybORG/Agents/Wrappers/IntListToAction.py) - converts the action classes and parameters into a list of integers
- [ReduceActionSpaceWrapper](CybORG/CybORG/Agents/Wrappers/ReduceActionSpaceWrapper.py) - removes parameters from the action space that are unused by any of the action classes
- [BlueTableWrapper](CybORG/CybORG/Agents/Wrappers/BlueTableWrapper.py) - aggregates information from observations and converts into a 1-dimensional vector of integers

### Reward Calculators

Depending on the agent and its actions, there are several rewards calculators utilized inside Cyborg. Those reward calculators are located in [Shared](CybORG/CybORG/Shared/). The main purpose of those reward calculators is to increase the red agent reward when it is doing something good, and decreasing the blue agent reward when it is doing something bad.

#### Red Agent Reward
- [PwnRewardCalculator](CybORG/CybORG/Shared/RedRewardCalculator.py)
- [DistruptRewardCalculator](CybORG/CybORG/Shared/RedRewardCalculator.py)
- [HybridImpactPwnRewardClculator](CybORG/CybORG/Shared/RedRewardCalculator.py)

#### Blue Agent Reward
- [ConfidentialityRewardCalculator](CybORG/CybORG/Shared/BlueRewardCalculator.py)
- [AvailabilityRewardCalculator](CybORG/CybORG/Shared/BlueRewardCalculator.py)
- [HybridAvailabilityConfidentialityRewardCalculator](CybORG/CybORG/Shared/BlueRewardCalculator.py)


### Simple Agents

Cyborg offers a variety of Blue, Red and Green agents to use in the Network. They can be
found at [SimpleAgents](CybORG/CybORG/Agents/SimpleAgents)

#### Multiple Agents
- [Sleep](/CybORG/CybORG/Agents/SimpleAgents/SleepAgent.py)
- [KeyboardAgent](/CybORG/CybORG/Agents/SimpleAgents/KeyboardAgent.py)
- [TestAgent](/CybORG/CybORG/Agents/SimpleAgents/TestAgent.py)

#### Red Agents
- [B_line](/CybORG/CybORG/Agents/SimpleAgents/B_line.py)
- [Meander](/CybORG/CybORG/Agents/SimpleAgents/Meander.py)
- [HeuristicRed](/CybORG/CybORG/Agents/SimpleAgents/HeuristicRed.py)

#### Blue Agents
- [BlueReact](/CybORG/CybORG/Agents/SimpleAgents/BlueReactAgent.py)
- [CounterKillchainAgent](/CybORG/CybORG/Agents/SimpleAgents/CounterKillchainAgent.py)
- [BlueMonitorAgent](/CybORG/CybORG/Agents/SimpleAgents/BlueMonitorAgent.py)



## How to Use

### Creating the environment

Create a CybORG environment with:
```
from CybORG import CybORG
PATH = str(inspect.getfile(CybORG))
PATH = PATH[:-10] + "/Shared/Scenarios/Scenario2.yaml"
cyborg = CybORG(PATH, "sim", agents={})
```
 
### Train and Evaluate

There are some sample scripts to [train](/CybORG/CybORG/Train/training.py) and [evaluate](/CybORG/CybORG/Train/evaluation.py) agents using stable-baselines3 library.