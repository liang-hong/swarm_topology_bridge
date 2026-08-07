#!/usr/bin/env python3
"""Topic bridge loopback/integration test node (chatter over ZMQ)."""
import rospy
from std_msgs.msg import String


def other_chatter_cb(msg, src_name):
    rospy.loginfo(
        "[TopicBridge] RECV %s -> us: %s", src_name, msg.data
    )


if __name__ == '__main__':
    rospy.init_node('test_swarm_chatter')

    # 1. 获取本机名称
    uav_name = rospy.get_param('~uav_name', 'unknown')
    rospy.loginfo("[TopicBridge] start for %s", uav_name)

    # 2. 发布本机消息
    pub = rospy.Publisher('chatter', String, queue_size=10)

    # 3. 根据拓扑订阅其他无人机/本机通过 Bridge 转发回来的消息
    # Bridge 将 src 的 chatter 发布到 /{src}/chatter
    topology = rospy.get_param('/swarm_bridge/topology', {})
    my_neighbors = topology.get(uav_name, [])

    for neighbor in my_neighbors:
        topic_name = "/{}/chatter".format(neighbor)
        rospy.Subscriber(topic_name, String, other_chatter_cb, neighbor)
        rospy.loginfo("[TopicBridge] subscribe %s", topic_name)

    # 4. 循环发布消息
    rate = rospy.Rate(1)  # 1Hz
    count = 0
    while not rospy.is_shutdown():
        msg = "Hello from {}! (count: {})".format(uav_name, count)
        rospy.loginfo("[TopicBridge] SEND %s", msg)
        pub.publish(msg)
        count += 1
        rate.sleep()
