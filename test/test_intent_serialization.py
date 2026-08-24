#!/usr/bin/env python3
import io
import unittest

from geometry_msgs.msg import Pose
from swarm_uav_interfaces.msg import UavTrajectoryIntent


class IntentSerializationTest(unittest.TestCase):
    def test_all_phases_survive_native_ros_roundtrip(self):
        for phase in (UavTrajectoryIntent.PHASE_TENTATIVE,
                      UavTrajectoryIntent.PHASE_ACTIVE,
                      UavTrajectoryIntent.PHASE_BRAKING):
            msg = UavTrajectoryIntent()
            msg.protocol_version = "2.0"
            msg.phase = phase
            msg.uav_id = "A02"
            msg.exec_target = "UAV2"
            msg.frame_id = "map"
            msg.traj_id = 17
            msg.stamp = 123.5
            msg.t = [0.0, 1.0]
            msg.sampled_traj = [Pose(), Pose()]
            msg.sampled_traj[1].position.x = 1.25
            msg.clearance = 0.5

            buffer = io.BytesIO()
            msg.serialize(buffer)
            decoded = UavTrajectoryIntent()
            decoded.deserialize(buffer.getvalue())

            self.assertEqual(decoded.protocol_version, "2.0")
            self.assertEqual(decoded.phase, phase)
            self.assertEqual(decoded.traj_id, 17)
            self.assertEqual(list(decoded.t), [0.0, 1.0])
            self.assertAlmostEqual(decoded.sampled_traj[1].position.x, 1.25)


if __name__ == "__main__":
    unittest.main()