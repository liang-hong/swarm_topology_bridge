#!/usr/bin/env python3
# 基于拓扑配置的 ROS ZeroMQ 桥接节点
# 功能:
#   1) Topic 桥 (ZMQ PUB/SUB), 保留 ROS 消息原生序列化与来源命名空间
#   2) 通用 Service 请求/响应代理 (ZMQ DEALER/ROUTER):
#      - 配置声明 Service 名称、类型、目标节点和超时
#      - 本机为每个远程 Service 注册同名 ROS Service, 上层 ROS 调用透明转发
#      - 每次请求携带 bridge 层唯一 request ID
#      - 支持并发请求、超时和迟到响应丢弃
#      - bridge 不理解任务业务, 只代理 ROS 序列化请求/响应
#
# 限频:
#   - 每个话题独立限频配置; max_freq 为 null/0 表示不限频
#   - 启动窗口首条消息永不丢弃
import rospy
import roslib.message
import zmq
import threading
import time
import socket
import io
from threading import Lock


def ensure_global(name):
    return name if name.startswith('/') else '/' + name


class BridgeNode:
    def __init__(self):
        # 1) 读取参数与本机标识
        self.ns = rospy.get_namespace()
        self.uavs = rospy.get_param('~uavs')
        self.topics = rospy.get_param('~topics')
        self.max_freq = float(rospy.get_param('~max_freq', 0))
        self.base_port = int(rospy.get_param('~base_port'))
        self.topology = rospy.get_param('~topology')
        self.services = rospy.get_param('~services', [])
        self.service_base_port = int(rospy.get_param('~service_base_port', self.base_port + 10000))

        override_name = rospy.get_param('~uav_name', None)
        self.my_name = override_name if override_name else socket.gethostname()

        name_set = set([u['name'] for u in self.uavs])
        if self.my_name not in name_set:
            my_ip = socket.gethostbyname(socket.gethostname())
            candidates = [u['name'] for u in self.uavs if u['ip'] == my_ip]
            if len(candidates) == 1:
                self.my_name = candidates[0]
            else:
                rospy.logerr("bridge: 无法根据 hostname/IP 解析本机 UAV 名称, 请在 launch 中设置参数 ~uav_name")
                raise RuntimeError("uav_name not resolved")

        # 2) 基础映射与上下文
        self.uav_ip = {u['name']: u.get('ip', '127.0.0.1') for u in self.uavs}
        self.topic_ports = {i: self.base_port + i for i in range(len(self.topics))}
        self.uav_port_offsets = {u['name']: int(u.get('port_offset', 0)) for u in self.uavs}

        self.context = zmq.Context.instance()
        self.pub_sockets = {}
        self.pub_locks = {}
        self.sub_sockets = []
        self.poller = zmq.Poller()
        self.socket_map = {}
        self.msg_classes = {}
        self.publishers = {}
        self.window_start = {}
        self.send_counts = {}
        # 每话题限频; None 表示不限频
        self.topic_limits = {}

        # 3) 动态加载消息类型
        for i, t in enumerate(self.topics):
            cls = roslib.message.get_message_class(t['type'])
            if cls is None:
                rospy.logerr("bridge: invalid msg type %s", t['type'])
                raise RuntimeError("invalid msg type %s" % t['type'])
            self.msg_classes[i] = cls
            limit = t.get('max_freq', self.max_freq)
            self.topic_limits[i] = None if limit is None or float(limit) <= 0 else float(limit)

        for i in range(len(self.topics)):
            self.window_start[i] = time.time()
            self.send_counts[i] = 0

        # 4) 初始化 ZMQ PUB
        my_offset = self.uav_port_offsets.get(self.my_name, 0)
        for i, _ in enumerate(self.topics):
            s = self.context.socket(zmq.PUB)
            s.bind("tcp://*:%d" % (self.topic_ports[i] + my_offset))
            self.pub_sockets[i] = s
            self.pub_locks[i] = Lock()
        rospy.loginfo("bridge: my_name=%s, port_offset=%d, topics=%d",
                      self.my_name, my_offset, len(self.topics))

        # 5) 初始化 ZMQ SUB 与对应 ROS Publisher
        src_list = self.topology.get(self.my_name, [])
        rospy.loginfo("bridge: recv sources=%s", ",".join(src_list) if src_list else "(none)")
        for src in src_list:
            ip = self.uav_ip[src]
            src_offset = self.uav_port_offsets.get(src, 0)
            for i in range(len(self.topics)):
                s = self.context.socket(zmq.SUB)
                s.setsockopt(zmq.SUBSCRIBE, b"")
                s.connect("tcp://%s:%d" % (ip, self.topic_ports[i] + src_offset))
                self.sub_sockets.append(s)
                self.poller.register(s, zmq.POLLIN)
                self.socket_map[s] = (src, i)
                pub_name = ensure_global(self.topics[i]['name'])
                pub_full = "/%s%s" % (src, pub_name)
                self.publishers[(src, i)] = rospy.Publisher(pub_full, self.msg_classes[i], queue_size=10)

        # 6) 初始化 ROS 订阅
        for i, t in enumerate(self.topics):
            sub_name = ensure_global(t['name'])
            cls = self.msg_classes[i]
            rospy.Subscriber(sub_name, cls, self._make_cb(i), queue_size=10)

        # 7) 启动 Topic 接收线程
        self.recv_thread = threading.Thread(target=self.recv_loop)
        self.recv_thread.daemon = True
        self.recv_thread.start()

        # 8) 初始化通用 Service 代理
        self._service_init()

    # ------------------------------------------------------------------ Topic
    def _make_cb(self, idx):
        def cb(msg):
            now = time.time()
            elapsed = now - self.window_start[idx]
            limit = self.topic_limits[idx]
            discard = False
            if limit is not None:
                # 首条消息永不丢弃; 滑窗内超过限频才丢弃
                if self.send_counts[idx] > 0 and elapsed > 0 and \
                        (self.send_counts[idx] + 1) / elapsed > limit:
                    discard = True
            if not discard:
                buff = io.BytesIO()
                msg.serialize(buff)
                payload = buff.getvalue()
                with self.pub_locks[idx]:
                    self.pub_sockets[idx].send(payload, flags=0)
                self.send_counts[idx] += 1
            # 滑窗重置: 周期为 1s
            if elapsed > 1.0:
                self.window_start[idx] = now
                self.send_counts[idx] = 0
        return cb

    def recv_loop(self):
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

    # --------------------------------------------------------------- Service
    def _service_init(self):
        """初始化通用 Service 请求/响应代理。

        规则 (每个节点加载同一份配置):
          - target == my_name: 本机是服务端, 绑定 ROUTER 端口, 收到跨机请求后
            调用本地同名 ROS Service 并返回序列化响应。
          - target != my_name: 本机是潜在请求端, 在本机注册同名 ROS Service,
            上层 ROS 调用时通过 ZMQ 转发到目标节点。
        """
        self.srv_classes = {}
        self.local_srv_proxies = {}   # name -> rospy.ServiceProxy (服务端用)
        self.dealers = {}             # target -> zmq.DEALER
        self.dealer_locks = {}
        self._request_counter = 0
        self._req_lock = Lock()
        self.pending_requests = {}    # request_id -> _PendingRequest
        self.dealer_recv_threads = []

        # 收集 service 定义
        for item in self.services:
            name = ensure_global(item['name'])
            srv_type = item['type']
            cls = roslib.message.get_service_class(srv_type)
            if cls is None:
                rospy.logerr("bridge: invalid service type %s", srv_type)
                raise RuntimeError("invalid service type %s" % srv_type)
            self.srv_classes[name] = cls

        # 服务端: 目标为本节点时绑定 ROUTER
        self.router = None
        if any(ensure_global(item['name']) in self.srv_classes and item.get('target') == self.my_name
               for item in self.services):
            my_offset = self.uav_port_offsets.get(self.my_name, 0)
            self.router = self.context.socket(zmq.ROUTER)
            self.router.bind("tcp://*:%d" % (self.service_base_port + my_offset))
            self.router_thread = threading.Thread(target=self._router_loop)
            self.router_thread.daemon = True
            self.router_thread.start()
            rospy.loginfo("bridge: service router bound on %d (my_name=%s)",
                          self.service_base_port + my_offset, self.my_name)

        # 请求端: 为每个远程 service 注册本地 ROS Service 代理
        for item in self.services:
            name = ensure_global(item['name'])
            target = item['target']
            if target == self.my_name:
                # 服务端: 缓存本地 ServiceProxy
                self.local_srv_proxies[name] = rospy.ServiceProxy(name, self.srv_classes[name], persistent=False)
            else:
                # 请求端: 注册本地 ROS Service, 转发到目标节点
                rospy.Service(name, self.srv_classes[name], self._make_service_handler(name, target))
                rospy.loginfo("bridge: proxying %s -> %s", name, target)
                self._ensure_dealer(target, item)

    def _ensure_dealer(self, target, item):
        if target in self.dealers:
            return
        ip = self.uav_ip[target]
        target_offset = self.uav_port_offsets.get(target, 0)
        dealer = self.context.socket(zmq.DEALER)
        dealer.connect("tcp://%s:%d" % (ip, self.service_base_port + target_offset))
        self.dealers[target] = dealer
        self.dealer_locks[target] = Lock()
        # 后台收线线程
        thread = threading.Thread(target=self._dealer_recv_loop, args=(target,))
        thread.daemon = True
        thread.start()
        self.dealer_recv_threads.append(thread)
        rospy.loginfo("bridge: dealer connected to %s service router %s:%d",
                      target, ip, self.service_base_port + target_offset)

    def _make_service_handler(self, name, target):
        def handler(req):
            request_id = self._new_request_id()
            buff = io.BytesIO()
            req.serialize(buff)
            payload = buff.getvalue()
            pending = _PendingRequest()
            with self._req_lock:
                self.pending_requests[request_id] = pending
            frames = [name.encode('utf-8'),
                      str(request_id).encode('ascii'),
                      payload]
            dealer = self.dealers[target]
            with self.dealer_locks[target]:
                try:
                    dealer.send_multipart(frames)
                except zmq.ZMQError as exc:
                    with self._req_lock:
                        self.pending_requests.pop(request_id, None)
                    raise rospy.ServiceException("bridge send failed: %s" % exc)
            if not pending.event.wait(timeout=pending.timeout):
                with self._req_lock:
                    self.pending_requests.pop(request_id, None)
                raise rospy.ServiceException(
                    "bridge service timeout for %s -> %s" % (name, target))
            # 迟到响应已在 recv 线程中被丢弃
            if pending.error is not None:
                raise rospy.ServiceException(pending.error)
            return pending.response
        return handler

    def _dealer_recv_loop(self, target):
        # DEALER 接收端: ROUTER 发送的 identity 帧会被 ZMQ 自动剥离,
        # 因此收到的是 3 帧: [service_name, request_id, payload]。
        dealer = self.dealers[target]
        while not rospy.is_shutdown():
            try:
                frames = dealer.recv_multipart(flags=0)
            except zmq.ZMQError:
                if rospy.is_shutdown():
                    return
                continue
            if len(frames) != 3:
                rospy.logwarn("bridge: dropping malformed service reply from %s (%d frames)", target, len(frames))
                continue
            name_b, req_id_b, resp_payload = frames
            request_id = int(req_id_b.decode('ascii'))
            with self._req_lock:
                pending = self.pending_requests.pop(request_id, None)
            if pending is None:
                # 迟到/未知响应 -> 丢弃
                continue
            if resp_payload and resp_payload[0] == 1:
                pending.error = resp_payload[1:].decode('utf-8', errors='replace')
                pending.event.set()
                continue
            name = name_b.decode('utf-8')
            srv_cls = self.srv_classes.get(name)
            if srv_cls is None:
                pending.error = "bridge: unknown service %s" % name
                pending.event.set()
                continue
            if resp_payload[:1] == b'\x00':
                resp_payload = resp_payload[1:]
            response = srv_cls._response_class()
            try:
                # genpy.Message.deserialize requires bytes (indexable), not BytesIO.
                response.deserialize(resp_payload)
            except Exception as exc:
                pending.error = "bridge: bad response payload: %s" % exc
                pending.event.set()
                continue
            pending.response = response
            pending.event.set()

    def _router_loop(self):
        while not rospy.is_shutdown():
            try:
                frames = self.router.recv_multipart(flags=0)
            except zmq.ZMQError:
                if rospy.is_shutdown():
                    return
                continue
            if len(frames) != 4:
                rospy.logwarn("bridge: dropping malformed service request (%d frames)", len(frames))
                continue
            identity, name_b, req_id_b, req_payload = frames
            name = name_b.decode('utf-8')
            srv_cls = self.srv_classes.get(name)
            proxy = self.local_srv_proxies.get(name)
            if srv_cls is None or proxy is None:
                self.router.send_multipart([identity, name_b, req_id_b,
                                            b'\x01' + ("bridge: no local service %s" % name).encode('utf-8')])
                continue
            request = srv_cls._request_class()
            try:
                # genpy.Message.deserialize requires bytes (indexable), not BytesIO.
                request.deserialize(req_payload)
            except Exception as exc:
                self.router.send_multipart([identity, name_b, req_id_b,
                                            b'\x01' + ("bridge: bad request payload: %s" % exc).encode('utf-8')])
                continue
            try:
                response = proxy(request)
            except rospy.ServiceException as exc:
                self.router.send_multipart([identity, name_b, req_id_b,
                                            b'\x01' + str(exc).encode('utf-8')])
                continue
            buff = io.BytesIO()
            response.serialize(buff)
            self.router.send_multipart([identity, name_b, req_id_b, b'\x00' + buff.getvalue()])

    def _new_request_id(self):
        with self._req_lock:
            self._request_counter += 1
            return self._request_counter


class _PendingRequest:
    def __init__(self, timeout=2.0):
        self.event = threading.Event()
        self.response = None
        self.error = None
        self.timeout = timeout


def main():
    rospy.init_node('swarm_bridge', anonymous=False)
    BridgeNode()
    rospy.spin()


if __name__ == '__main__':
    main()