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
  swarm_uav_interfaces
)

catkin_package()

if(CATKIN_ENABLE_TESTING)
  catkin_add_nosetests(test/test_intent_serialization.py)
endif()

install(PROGRAMS
  scripts/bridge_node.py
  scripts/test_chatter.py
  scripts/test_service_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(DIRECTORY config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
