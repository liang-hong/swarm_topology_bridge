#!/usr/bin/env python3
# 基于拓扑配置的 ROS ZeroMQ 桥接节点
# 目标：通过单一 YAML 配置（无人机清单、话题列表、统一频率、拓扑关系）
# 在运行时完成 ZMQ PUB/SUB 建立、ROS 话题订阅/发布的桥接，修改配置无需重新编译
import rospy
import roslib.message
import zmq
import threading
import time
import socket
import io
from threading import Lock

# 工具函数：确保话题名为全局命名（以 / 开头）
def ensure_global(name):
    return name if name.startswith('/') else '/' + name

# 桥接节点主体
class BridgeNode:
    def __init__(self):
        # 1) 读取参数与本机标识
        # uavs: [{name, ip}], topics: [{name, type}], max_freq: 统一限速(Hz), base_port: 端口基准, topology: {uav_name: [src_names]}
        self.ns = rospy.get_namespace()
        self.uavs = rospy.get_param('~uavs')
        self.topics = rospy.get_param('~topics')
        self.max_freq = int(rospy.get_param('~max_freq'))
        self.base_port = int(rospy.get_param('~base_port'))
        self.topology = rospy.get_param('~topology')

        # 优先使用 ~uav_name 显式指定本机 UAV 名称；否则用 hostname 推断
        override_name = rospy.get_param('~uav_name', None)
        self.my_name = override_name if override_name else socket.gethostname()

        # 校验 my_name 是否在配置的 uavs 列表中；若不在，再尝试通过本机 IP 匹配
        name_set = set([u['name'] for u in self.uavs])
        if self.my_name not in name_set:
            my_ip = socket.gethostbyname(socket.gethostname())
            candidates = [u['name'] for u in self.uavs if u['ip'] == my_ip]
            if len(candidates) == 1:
                self.my_name = candidates[0]
            else:
                rospy.logerr("bridge: 无法根据 hostname/IP 解析本机 UAV 名称，请在 launch 中设置参数 ~uav_name")
                raise RuntimeError("uav_name not resolved")

        # 2) 基础映射与上下文
        self.uav_ip = {u['name']: u['ip'] for u in self.uavs}
        self.topic_ports = {i: self.base_port + i for i in range(len(self.topics))}
        self.context = zmq.Context.instance()
        self.pub_sockets = {}
        self.pub_locks = {}
        self.sub_sockets = []
        self.poller = zmq.Poller()
        self.socket_map = {}
        self.msg_classes = {}
        self.publishers = {}
        self.recv_flags_last = {}
        self.window_start = {}
        self.send_counts = {}

        # 3) 动态加载消息类型（运行时按 rosmsg 名称解析）
        for i, t in enumerate(self.topics):
            cls = roslib.message.get_message_class(t['type'])
            if cls is None:
                rospy.logerr("bridge: invalid msg type %s", t['type'])
                raise RuntimeError("invalid msg type %s" % t['type'])
            self.msg_classes[i] = cls

        # 初始化频率控制窗口（每话题独立 1s 滑窗）
        for i in range(len(self.topics)):
            self.window_start[i] = time.time()
            self.send_counts[i] = 0

        # 4) 初始化 ZMQ PUB：本机为每个话题绑定 tcp://*:<base_port+i>
        for i, _ in enumerate(self.topics):
            s = self.context.socket(zmq.PUB)
            s.bind("tcp://*:%d" % self.topic_ports[i])
            self.pub_sockets[i] = s
            self.pub_locks[i] = Lock()
        rospy.loginfo("bridge: my_name=%s, topics=%d", self.my_name, len(self.topics))

        # 5) 初始化 ZMQ SUB 与对应 ROS Publisher：
        # 对 topology[my_name] 列表中的每个源无人机，为每个话题建立 SUB 连接；
        # 接收后发布到 /源名/话题名，避免同名话题冲突
        src_list = self.topology.get(self.my_name, [])
        rospy.loginfo("bridge: recv sources=%s", ",".join(src_list) if src_list else "(none)")
        for src in src_list:
            ip = self.uav_ip[src]
            for i in range(len(self.topics)):
                s = self.context.socket(zmq.SUB)
                s.setsockopt(zmq.SUBSCRIBE, b"")
                s.connect("tcp://%s:%d" % (ip, self.topic_ports[i]))
                self.sub_sockets.append(s)
                self.poller.register(s, zmq.POLLIN)
                self.socket_map[s] = (src, i)
                self.recv_flags_last[(src, i)] = False
                pub_name = ensure_global(self.topics[i]['name'])
                pub_full = "/%s%s" % (src, pub_name)
                self.publishers[(src, i)] = rospy.Publisher(pub_full, self.msg_classes[i], queue_size=10)

        # 6) 初始化 ROS 订阅：订阅本机的统一话题列表，发送到对应 ZMQ PUB
        for i, t in enumerate(self.topics):
            sub_name = ensure_global(t['name'])
            cls = self.msg_classes[i]
            rospy.Subscriber(sub_name, cls, self._make_cb(i), queue_size=10)

        # 7) 启动接收线程：轮询 ZMQ SUB，反序列化并发布到 /源名/话题名
        self.recv_thread = threading.Thread(target=self.recv_loop)
        self.recv_thread.daemon = True
        self.recv_thread.start()

    def _make_cb(self, idx):
        # 发送回调（按统一频率限速）
        def cb(msg):
            now = time.time()
            elapsed = now - self.window_start[idx]
            discard = False
            # 若窗口内实际频率将超出 max_freq，则丢弃本次消息
            if elapsed > 0 and (self.send_counts[idx] + 1) / elapsed > self.max_freq:
                discard = True
            if not discard:
                # 序列化 ROS 消息为字节并通过 ZMQ 发送
                buff = io.BytesIO()
                msg.serialize(buff)
                payload = buff.getvalue()
                with self.pub_locks[idx]:
                    self.pub_sockets[idx].send(payload, flags=0)
                self.send_counts[idx] += 1
            # 滑窗重置：周期为 1s
            if elapsed > 1.0:
                self.window_start[idx] = now
                self.send_counts[idx] = 0
        return cb

    def recv_loop(self):
        # 接收循环：轮询所有 SUB 套接字，反序列化并发布到 /源名/话题名
        while not rospy.is_shutdown():
            events = dict(self.poller.poll(timeout=100))
            for s in events:
                if events[s] == zmq.POLLIN:
                    payload = s.recv(flags=0)
                    src, idx = self.socket_map[s]
                    cls = self.msg_classes[idx]
                    msg = cls()
                    msg.deserialize(payload)
                    self.publishers[(src, idx)].publish(msg)
                    key = (src, idx)
                    if not self.recv_flags_last[key]:
                        pub_name = ensure_global(self.topics[idx]['name'])
                        # 首次接收到某源某话题时打印提示
                        full_name = "/%s%s" % (src, pub_name)
                        rospy.loginfo('"%s" received', full_name)
                        self.recv_flags_last[key] = True

def main():
    # 节点入口：初始化 ROS 节点并启动桥接
    rospy.init_node('swarm_bridge', anonymous=False)
    BridgeNode()
    rospy.spin()

if __name__ == '__main__':
    main()
