# swarm_topology_bridge

[English] | [中文](README.md)

A topology-driven ROS bridge using ZeroMQ (Python), configurable at runtime without recompilation. Deployed as a generic communication component on all ROS nodes for multi-ROS interaction.

## Introduction
- A lightweight ROS bridge node that forwards selected ROS topics between robots over ZeroMQ sockets.
- Designed for swarm scenarios where flexible peer discovery and topic selection matter.
- Supports both **real-world multi-UAV deployment** and **single-machine multi-master simulation**.
- In addition to the Topic bridge, it provides a **generic ROS Service request/response proxy** (ZMQ DEALER/ROUTER) for synchronous task/safety requests across masters, while staying transparent to business types (message/service types are resolved dynamically from config).

## Benefits
- **Decentralized**: No central ROS master dependency; peers can launch in any order and connect autonomously.
- **Configurable**: Define exactly which topics and services to send/receive instead of mirroring everything.
- **Easy to use**: Manage IPs, topics, services, and simulation **port offsets** in a single YAML file.
- **Namespace isolation**: Adds the source UAV name as a namespace (e.g., `/UAV6/pose`) to avoid topic name collisions.
- **Generic**: This package does not take part in task business; it only bridges ROS natively serialized topics/services. Retries and idempotency are left to the upper business layer.

## Structure
```bash
└── swarm_topology_bridge
    ├── CMakeLists.txt
    ├── LICENSE
    ├── README.md                 # Chinese primary README
    ├── README-en.md              # English README
    ├── config
    │   ├── topology.yaml             # Default config for real hardware
    │   ├── topology_sim_swarm.yaml   # Config for multi-master simulation
    │   └── topology_sim_single.yaml  # Config for single-node loopback test
    ├── launch
    │   ├── test.launch               # Example launch for real-world application
    │   ├── test_sim_swarm.launch     # Launch for multi-master simulation test
    │   └── test_sim_single.launch    # Launch for single-node loopback test
    ├── package.xml
    └── scripts
        ├── bridge_node.py            # Core bridge node (Topic bridge + Service proxy)
        ├── test_chatter.py           # Connectivity test script
        ├── test_swarm_chatter.py     # Multi-robot connectivity test script
        └── test_service_node.py      # Generic Service proxy test script
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

> **Note**: This package is developed using `catkin_tools`. `catkin build` is recommended for isolated builds, but it remains fully compatible with the traditional `catkin_make`.

## Usage

### 1. Topic Bridge

#### 1.1 Real Hardware Deployment
Edit `config/topology.yaml` to set physical IPs and topics.
```bash
roslaunch swarm_topology_bridge test.launch
```

#### 1.2 Multi-Master Simulation (Single Machine)
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

#### 1.3 Single Node Loopback
```bash
roslaunch swarm_topology_bridge test_sim_single.launch
```

#### 1.4 Topic Rate Limit
- Each topic can set its own `max_freq` (`null`/`0` means unlimited). Control/status topics are recommended to be unlimited to avoid drops.
- The first message right after startup is never dropped by the rate limiter.

### 2. Generic Service Request/Response Proxy

Declare service name, type and target node in the `~services` config, e.g.:

```yaml
services:
  - {name: /UAV1/uav_task, type: your_pkg/YourTaskSrv, target: UAV1}
  - {name: /UAV1/uav_hold, type: your_pkg/YourHoldSrv, target: UAV1}
```

Convention (every node loads the same config and decides its role by `target`):

- If this node is the `target`: it binds a ZMQ ROUTER port, invokes the local ROS Service with the same name, and returns the serialized response.
- Otherwise: it registers a same-named ROS Service proxy on the local master and forwards calls over ZMQ to the target node.
- Every request carries a bridge-level unique request ID; concurrent requests, timeouts and late replies are supported/dropped.
- The bridge only proxies ROS serialized requests/responses and does not understand task business.

See the business package config (e.g., `tcp_to_ros/config/topology_group_a_sim.yaml`) for a Group A integration example.

### 3. Service Proxy Test (Built-in)

The package ships `test_service_node.py` (uses `std_srvs/SetBool`, no business package dependency):

- Each node provides `/test_srv/{uav_name}`;
- Periodically calls `/test_srv/{target}` of its topology neighbours (note: the target side registers the local service via ROUTER, the caller side registers a local proxy and forwards; loopback uses the same node for both roles);
- All three launch files (real `test.launch`, sim swarm `test_sim_swarm.launch`, loopback `test_sim_single.launch`) start this test node by default, and their paired configs already declare the matching `services`;
- `[Test] <local> -> /test_srv/<target> success=True` in the terminal log means the cross-master (or loopback) Service proxy link is healthy.

```bash
# Sim multi-robot example: run per ROS Master
roslaunch swarm_topology_bridge test_sim_swarm.launch uav_name:=UAV6
# Real robot example: run on each onboard computer (hostname inferred, or pass uav_name)
roslaunch swarm_topology_bridge test.launch uav_name:=UAV6
```

## Relation to other projects
- Inspired by the C++ project [swarm_ros_bridge](https://github.com/shupx/swarm_ros_bridge).
- This repository is a Python rewrite optimized for configuration flexibility, Service proxy and simulation support.

## License
- BSD-3-Clause