# swarm_topology_bridge

[English] | [中文](README_zh.md)

Topology-driven ROS bridge using ZeroMQ (Python), configurable at runtime without recompilation.

## Introduction
- A lightweight ROS bridge that transmits specified ROS topics across robots using ZeroMQ sockets.
- Designed for swarm scenarios where peer discovery and flexible topic selection are important.
- Supports both **real-world** multi-UAV deployment and **single-machine multi-master** simulation.

## Benefits
- **Robust**: No central ROS master dependency; peers can launch in any order and connect autonomously.
- **Flexible**: Configure only the topics you need to send/receive instead of mirroring all topics.
- **Easy to use**: Manage IPs, topics, and **port offsets** for simulation in a single YAML file.
- **Namespace isolation**: Automatically adds source UAV names as namespaces (e.g., `/UAV6/pose`) to prevent topic name collisions.

## Structure
```bash
└── swarm_topology_bridge
    ├── CMakeLists.txt
    ├── config
    │   ├── topology.yaml             # Default config for real hardware
    │   ├── topology_sim_swarm.yaml   # Config for multi-master simulation
    │   └── topology_sim_single.yaml  # Config for single-node loopback test
    ├── launch
    │   ├── test.launch
    │   ├── test_sim_swarm.launch     # Launch for multi-master simulation test
    │   └── test_sim_single.launch    # Launch for single-node loopback test
    ├── package.xml
    └── scripts
        ├── bridge_node.py            # Core bridge node
        └── test_swarm_chatter.py     # General chatter test script
```

## Install
- Supported: ROS1 (e.g., Melodic/Noetic) on Ubuntu; Python 3.
- Dependencies: `sudo apt install python3-zmq` or `pip3 install zmq`

```bash
# create workspace
mkdir -p catkin_ws/src && cd catkin_ws/src
# clone
git clone https://github.com/liang-hong/swarm_topology_bridge.git
# build
cd ..
catkin build swarm_topology_bridge
source devel/setup.bash
```

> **Note**: This package is developed using `catkin_tools`. It is highly recommended to use `catkin build` for isolated builds. However, it remains fully compatible with the traditional `catkin_make` if required by your workspace setup.

## Usage

### 1. Real Hardware Deployment
Edit `config/topology.yaml` to set physical IPs and topics.
```bash
roslaunch swarm_topology_bridge test.launch
```

### 2. Multi-Master Simulation (Single Machine)
This mode simulates multiple independent onboard computers using `port_offset`.
1. **Terminal 1 (UAV6)**:
   ```bash
   export ROS_MASTER_URI=http://localhost:11311
   roslaunch swarm_topology_bridge test_sim_swarm.launch uav_name:=UAV6
   ```
2. **Terminal 2 (UAV7)**:
   ```bash
   export ROS_MASTER_URI=http://localhost:11312
   roslaunch swarm_topology_bridge test_sim_swarm.launch uav_name:=UAV7
   ```

### 3. Single Node Loopback
```bash
roslaunch swarm_topology_bridge test_sim_single.launch
```

## Relation to other projects
- Inspired by the C++ project [swarm_ros_bridge](https://github.com/shupx/swarm_ros_bridge).
- This repository is a Python rewrite optimized for configuration flexibility and simulation support.

## License
- BSD-3-Clause
