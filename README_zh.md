# swarm_topology_bridge

[English](README.md) | [中文]

基于 ZeroMQ (Python) 的拓扑驱动型 ROS 桥接工具，运行时配置，无需重新编译。

## 简介
- 一款轻量级的 ROS 桥接节点，利用 ZeroMQ 套接字在不同机器人之间传输指定的 ROS 话题。
- 专为集群场景设计，强调节点发现的灵活性和话题选择的可控性。
- 同时支持**实机多机部署**与**单机多 Master 隔离仿真**。

## 优势
- **去中心化**：不依赖统一的 ROS Master；各节点可按任意顺序启动并自动建立连接。
- **配置灵活**：在 YAML 中精确定义发送/接收的话题，避免冗余数据传输。
- **易于使用**：在一个配置文件中管理所有 IP、话题以及用于仿真的**端口偏移 (Port Offset)**。
- **命名空间隔离**：自动为接收到的远程话题添加来源无人机前缀（如 `/UAV6/pose`），有效防止集群中同名话题冲突。

## 文件结构
```bash
└── swarm_topology_bridge
    ├── CMakeLists.txt
    ├── config
    │   ├── topology.yaml             # 实机部署默认配置
    │   ├── topology_sim_swarm.yaml   # 多 Master 联合仿真配置
    │   └── topology_sim_single.yaml  # 单机回环测试配置
    ├── launch
    │   ├── test.launch
    │   ├── test_sim_swarm.launch     # 仿真多机集成测试启动文件
    │   └── test_sim_single.launch    # 仿真单机回环测试启动文件
    ├── package.xml
    └── scripts
        ├── bridge_node.py            # 核心桥接节点
        └── test_swarm_chatter.py     # 通用连通性测试脚本
```

## 安装
- 支持环境：Ubuntu 上的 ROS1 (如 Melodic/Noetic)；Python 3。
- 依赖项：`sudo apt install python3-zmq` 或 `pip3 install zmq`

```bash
# 创建工作空间
mkdir -p catkin_ws/src && cd catkin_ws/src
# 克隆仓库
git clone https://github.com/liang-hong/swarm_topology_bridge.git
# 编译
cd ..
catkin build swarm_topology_bridge
source devel/setup.bash
```

> **注意**：本项目推荐使用 `catkin_tools` 进行编译。使用 `catkin build` 可以实现更好的包隔离和并行编译。同时，本项目依然完全兼容传统的 `catkin_make` 编译方式，您可以根据现有工作空间的习惯进行选择。

## 使用说明

### 1. 实机部署
修改 `config/topology.yaml` 以设置物理 IP 和需要传输的话题。
```bash
roslaunch swarm_topology_bridge test.launch
```

### 2. 多 Master 联合仿真 (单机模拟)
通过 `port_offset` 模拟多台独立的机载电脑环境。
1. **终端 1 (模拟 UAV6)**:
   ```bash
   export ROS_MASTER_URI=http://localhost:11311
   roslaunch swarm_topology_bridge test_sim_swarm.launch uav_name:=UAV6
   ```
2. **终端 2 (模拟 UAV7)**:
   ```bash
   export ROS_MASTER_URI=http://localhost:11312
   roslaunch swarm_topology_bridge test_sim_swarm.launch uav_name:=UAV7
   ```

### 3. 单机回环测试
```bash
roslaunch swarm_topology_bridge test_sim_single.launch
```

## 项目渊源
- 受 C++ 项目 [swarm_ros_bridge](https://github.com/shupx/swarm_ros_bridge) 启发。
- 本仓库为 Python 重构版本，针对配置灵活性和仿真适配进行了优化。

## 许可
- BSD-3-Clause
