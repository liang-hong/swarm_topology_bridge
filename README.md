# swarm_topology_bridge

[English](README-en.md) | [中文]

基于 ZeroMQ (Python) 的拓扑驱动型 ROS 桥接工具，运行时配置，无需重新编译。作为通用通信组件部署在 GCS 地面站与各无人机机载电脑上，不依赖任何业务功能包。

## 简介
- 一款轻量级的 ROS 桥接节点，利用 ZeroMQ 套接字在不同机器人之间传输指定的 ROS 话题。
- 专为集群场景设计，强调节点发现的灵活性和话题选择的可控性。
- 同时支持**实机多机部署**与**单机多 Master 隔离仿真**。
- 在 Topic 桥基础上，提供**通用 ROS Service 请求/响应代理**（ZMQ DEALER/ROUTER），支持跨 Master 的同步任务/安全请求，并保持对业务类型的透明（按配置动态解析消息类型）。

## 优势
- **去中心化**：不依赖统一的 ROS Master；各节点可按任意顺序启动并自动建立连接。
- **配置灵活**：在 YAML 中精确定义发送/接收的话题与要代理的 Service，避免冗余数据传输。
- **易于使用**：在一个配置文件中管理所有 IP、话题、Service 以及用于仿真的**端口偏移 (Port Offset)**。
- **命名空间隔离**：自动为接收到的远程话题添加来源无人机前缀（如 `/UAV6/pose`），有效防止集群中同名话题冲突。
- **通用性**：本包不理解任务业务，只做 ROS 原生序列化的 Topic 桥与 Service 代理；业务重试与幂等由上层业务包负责。

## 文件结构
```bash
└── swarm_topology_bridge
    ├── CMakeLists.txt
    ├── LICENSE
    ├── README.md                 # 中文主 README
    ├── README-en.md              # 英文 README
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
        ├── bridge_node.py            # 核心桥接节点（Topic 桥 + Service 代理）
        ├── test_chatter.py           # 连通性测试脚本
        └── test_swarm_chatter.py     # 多机连通性测试脚本
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

### 1. Topic 桥

#### 1.1 实机部署
修改 `config/topology.yaml` 以设置物理 IP 和需要传输的话题。
```bash
roslaunch swarm_topology_bridge test.launch
```

#### 1.2 多 Master 联合仿真 (单机模拟)
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

#### 1.3 单机回环测试
```bash
roslaunch swarm_topology_bridge test_sim_single.launch
```

#### 1.4 Topic 限频
- 每个话题可独立配置 `max_freq`（`null`/`0` 表示不限频），任务状态/控制类话题建议不限频以免丢消息；
- 启动窗口内的首条消息永不被限频逻辑丢弃。

### 2. 通用 Service 请求/响应代理

在 `~services` 配置中声明 Service 名称、类型与目标节点，示例：

```yaml
services:
  - {name: /UAV1/uav_task, type: your_pkg/YourTaskSrv, target: UAV1}
  - {name: /UAV1/uav_hold, type: your_pkg/YourHoldSrv, target: UAV1}
```

约定（每个节点加载同一份配置，按 `target` 判断角色）：

- 本机是 `target` 时：绑定 ZMQ ROUTER 端口，收到跨机请求后调用本机同名 ROS Service 并返回序列化响应；
- 本机不是 `target` 时：在本机 ROS Master 注册同名 Service 代理，收到上层调用后经 ZMQ 转发到目标节点；
- 每次请求携带 bridge 层唯一 request ID，支持并发请求、超时与迟到响应丢弃；
- bridge 只代理 ROS 序列化请求/响应，不理解任务业务。

具体配置示例见业务包（如 `tcp_to_ros/config/topology_group_a_sim.yaml`）的 Group A 联调部署。

## 项目渊源
- 受 C++ 项目 [swarm_ros_bridge](https://github.com/shupx/swarm_ros_bridge) 启发。
- 本仓库为 Python 重构版本，针对配置灵活性、Service 代理和仿真适配进行了优化。

## 许可
- BSD-3-Clause

## 相关文档
- 通用桥接方案与 Group A 应用：`tcp_to_ros` 地面站主包文档（`docs/tcp_to_ros_后续开发计划.md`）与 `docs/tcp_to_ros_测试记录.md`
- 机载应用示例（依赖本包）：`safe_valley_exp`