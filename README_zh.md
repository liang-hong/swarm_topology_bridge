swarm_topology_bridge

[English](README.md) | 中文

基于 ZeroMQ 的拓扑驱动 ROS 桥（Python 实现），支持运行时配置，无需重新编译。

介绍
- 通过 ZeroMQ 套接字在多机器人之间传输指定的 ROS 主题的轻量桥接节点。
- 面向集群/编队场景，强调灵活的主题选择与对等发现。

优势
- 稳健：不依赖中心 ROS master，节点可任意顺序启动并自主连接。
- 灵活：仅配置需要的发送/接收主题，而非镜像所有主题。
- 易用：在单个 YAML 文件中管理 IP 与主题。
- 可靠/轻量：基于 TCP 的 ZeroMQ PUB/SUB 更适合无线环境下的稳健传输。

目录结构
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

安装
- 支持：ROS1（如 Kinetic/Melodic/Noetic）与 Python 的 rospy/roslib 运行环境。
- 步骤：
```bash
# 创建工作区
mkdir -p ws/src && cd ws/src
# 克隆仓库
git clone https://github.com/liang-hong/swarm_topology_bridge.git
# 编译
cd ..
catkin build swarm_topology_bridge
source devel/setup.bash
```

使用
1. 编辑 config/topology.yaml（或 topology_sim_single.yaml），设置 IP、端口与主题。
2. 启动：
```bash
roslaunch swarm_topology_bridge test.launch
# 或
roslaunch swarm_topology_bridge latency_test_single.launch
```
3. 向配置的发送主题发布消息，检查远端接收主题是否正确收到；首次接收会打印 INFO。

与其他仓库的关系
- 参考来源：C++ 项目 swarm_ros_bridge（上游链接：https://github.com/shupx/swarm_ros_bridge）。
- 独立重构：本仓库非 fork，借鉴其设计与接口约定；不直接复制源代码。如确有少量片段引用，将在文件头标注来源与版权。

许可证
- BSD-3-Clause（详见 LICENSE 与 package.xml）。

关键词
- ros、zeromq、bridge、swarm、topology、python
