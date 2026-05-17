#!/usr/bin/env python3
import rospy
from std_msgs.msg import String

def other_chatter_cb(msg, name):
    rospy.loginfo(f"[Test] Received from {name}: {msg.data}")

if __name__ == '__main__':
    rospy.init_node('test_swarm_chatter')
    
    # 1. 获取本机名称
    uav_name = rospy.get_param('~uav_name', 'unknown')
    rospy.loginfo(f"[Test] Starting chatter test for {uav_name}")
    
    # 2. 发布本机消息
    pub = rospy.Publisher('chatter', String, queue_size=10)
    
    # 3. 根据拓扑订阅其他无人机通过 Bridge 转发回来的消息
    # 假设 Bridge 会将 src 的 chatter 发布到 /{src}/chatter
    topology = rospy.get_param('/swarm_bridge/topology', {})
    my_neighbors = topology.get(uav_name, [])
    
    for neighbor in my_neighbors:
        topic_name = f"/{neighbor}/chatter"
        rospy.Subscriber(topic_name, String, other_chatter_cb, neighbor)
        rospy.loginfo(f"[Test] Subscribed to {topic_name}")

    rate = rospy.Rate(1) # 1Hz
    count = 0
    while not rospy.is_shutdown():
        msg = f"Hello from {uav_name}! (count: {count})"
        pub.publish(msg)
        count += 1
        rate.sleep()
