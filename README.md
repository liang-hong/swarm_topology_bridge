swarm_topology_bridge

[English] | [中文](README_zh.md)

Topology-driven ROS bridge using ZeroMQ (Python), configurable at runtime without recompilation.

Introduction
- A lightweight ROS bridge that transmits specified ROS topics across robots using ZeroMQ sockets.
- Designed for swarm scenarios where peer discovery and flexible topic selection are important.

Benefits
- Robust: No central ROS master dependency; peers can launch in any order and connect autonomously.
- Flexible: Configure only the topics you need to send/receive instead of mirroring all topics.
- Easy to use: Manage IPs and topics in a single YAML file.
- Reliable/Lightweight: TCP-based ZeroMQ PUB/SUB provides robust links for wireless environments.

Structure
```bash
└── swarm_topology_bridge
    ├── CMakeLists.txt
    ├── config
    │   ├── topology.yaml
    │   └── topology_sim_single.yaml
    ├── launch
    │   ├── test.launch
    │   └── latency_test_single.launch
    ├── package.xml
    └── scripts
        └── bridge_node.py
```

Install
- Supported: ROS1 (e.g., Kinetic/Melodic/Noetic) on Ubuntu; Python rospy/roslib runtime.
- Steps:
```bash
# create workspace
mkdir -p ws/src && cd ws/src
# clone
git clone https://github.com/liang-hong/swarm_topology_bridge.git
# build
cd ..
catkin_make
source devel/setup.bash
```

Usage
1. Edit config/topology.yaml (or topology_sim_single.yaml) to set IPs, ports, and topics.
2. Launch:
```bash
roslaunch swarm_topology_bridge test.launch
# or
roslaunch swarm_topology_bridge latency_test_single.launch
```
3. Publish to configured send topics and verify that remote receive topics get data; first messages log INFO.

Relation to other projects
- Reference: C++ project swarm_ros_bridge (upstream: https://github.com/shupx/swarm_ros_bridge).
- This repository is an independent rewrite (not a fork). It follows similar design and interface ideas without directly copying source code. If small code fragments are referenced, the file header will include origin and copyright.

License
- BSD-3-Clause (see LICENSE and package.xml).

Keywords
- ros, zeromq, bridge, swarm, topology, python
