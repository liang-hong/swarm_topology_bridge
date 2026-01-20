cmake_minimum_required(VERSION 3.0.2)
project(swarm_topology_bridge)

find_package(catkin REQUIRED COMPONENTS
  rospy
  roslib
  std_msgs
  geometry_msgs
  sensor_msgs
  nav_msgs
  mavros_msgs
)

catkin_package()

install(PROGRAMS
  scripts/bridge_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(DIRECTORY config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
