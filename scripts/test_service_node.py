#!/usr/bin/env python3
"""Service proxy test node for swarm_topology_bridge.

Each node:
- provides ``/test_srv/{uav_name}`` (std_srvs/SetBool) as a local ROS Service;
- periodically calls ``/test_srv/{target}`` for every target in its topology
  neighbours, which is forwarded by the local bridge over ZMQ to the target's
  ROS Master (DEALER -> ROUTER).

This proves the generic Service request/response proxy works across ROS Masters
without depending on any business package (types are std_srvs built-ins).
"""

import socket

import rospy
from std_srvs.srv import SetBool, SetBoolRequest, SetBoolResponse


def _build_request(uav_name: str) -> SetBoolRequest:
    req = SetBoolRequest()
    req.data = True
    return req


def handle_test_service(req: SetBoolRequest) -> SetBoolResponse:
    rospy.loginfo(
        "[ServiceProxy] SERVE %s request data=%s", rospy.get_name(), req.data
    )
    resp = SetBoolResponse()
    resp.success = True
    resp.message = "ok"
    return resp


def main() -> None:
    rospy.init_node("test_service_node", anonymous=False)
    # 与 bridge 一致: 未显式给定 uav_name 时用 hostname 推断本机身份。
    uav_name = rospy.get_param("~uav_name", "") or socket.gethostname()

    service_name = "/test_srv/{}".format(uav_name)
    rospy.Service(service_name, SetBool, handle_test_service)
    rospy.loginfo("[ServiceProxy] provide %s", service_name)

    # Topology neighbour targets come from the shared config loaded by bridge.
    topology = rospy.get_param("/swarm_bridge/topology", {})
    targets = topology.get(uav_name, [])
    rospy.loginfo("[ServiceProxy] call targets: %s", targets)

    rate = rospy.Rate(0.5)  # one call every 2s
    while not rospy.is_shutdown():
        for target in targets:
            call_name = "/test_srv/{}".format(target)
            try:
                rospy.wait_for_service(call_name, timeout=2.0)
                proxy = rospy.ServiceProxy(call_name, SetBool)
                resp = proxy(_build_request(uav_name))
                rospy.loginfo(
                    "[ServiceProxy] CALL %s -> %s success=%s msg=%s",
                    uav_name, call_name, resp.success, resp.message,
                )
            except rospy.ROSException as exc:
                rospy.logwarn(
                    "[ServiceProxy] %s -> %s unavailable: %s", uav_name, call_name, exc
                )
        rate.sleep()


if __name__ == "__main__":
    main()