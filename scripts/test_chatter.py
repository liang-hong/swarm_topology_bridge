#!/usr/bin/env python3
import rospy
from std_msgs.msg import String

if __name__ == '__main__':
    rospy.init_node('test_chatter_publisher')
    pub = rospy.Publisher('chatter', String, queue_size=10)
    rate = rospy.Rate(1)  # 10Hz
    count = 0
    while not rospy.is_shutdown():
        message = f"Hello World! {count}"
        pub.publish(message)
        rospy.loginfo(f"Published: {message}")
        count += 1
        rate.sleep()