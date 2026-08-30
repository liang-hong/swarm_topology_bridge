#!/usr/bin/env python3
"""geographic_msgs 依赖与动态消息解析检查 (implementation_plan_26083018 §5).

bridge_node.py 运行时用 roslib.message.get_message_class 动态解析 topology
中的消息类型；topology_group_a_sim.yaml 使用 geographic_msgs/GeoPointStamped，
因此 package.xml / CMakeLists.txt 必须声明 geographic_msgs，否则按包清单
安装的干净环境无法启动 bridge 或解析 gp_origin。
"""
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import roslib.message

PACKAGE = Path(__file__).resolve().parents[1]
PACKAGE_XML = PACKAGE / "package.xml"
CMAKE = PACKAGE / "CMakeLists.txt"
TOPOLOGY = PACKAGE / "config" / "topology_group_a_sim.yaml"


class GeographicDependencyTest(unittest.TestCase):
    def test_geopointstamped_resolves_dynamically(self):
        # bridge 实际解析路径：roslib.message.get_message_class(type)
        cls = roslib.message.get_message_class("geographic_msgs/GeoPointStamped")
        self.assertIsNotNone(cls, "geographic_msgs/GeoPointStamped 必须可动态解析")

    def test_package_xml_declares_geographic_msgs(self):
        root = ET.parse(str(PACKAGE_XML)).getroot()
        deps = {child.tag for child in root
                if child.tag in ("build_depend", "build_export_depend",
                                 "exec_depend", "depend")}
        # format=2 下 <depend> 展开为 build+export+exec；兼容显式三种写法。
        explicit = {(dep.tag, dep.text)
                    for dep in root if dep.text == "geographic_msgs"}
        self.assertTrue(
            any(tag in deps for tag in ("build_depend", "build_export_depend",
                                        "exec_depend", "depend"))
            and explicit,
            "package.xml 必须声明 geographic_msgs（build/build_export/exec 或 depend）")
        declared = {tag for tag, _ in explicit}
        self.assertTrue(
            declared & {"build_depend", "depend"},
            "geographic_msgs 必须含 build 声明")
        self.assertTrue(
            declared & {"build_export_depend", "depend"},
            "geographic_msgs 必须含 build_export 声明")
        self.assertTrue(
            declared & {"exec_depend", "depend"},
            "geographic_msgs 必须含 exec 声明")

    def test_cmake_declares_geographic_msgs(self):
        cmake = CMAKE.read_text(encoding="utf-8")
        find_block = cmake.split("find_package(catkin REQUIRED COMPONENTS", 1)[1]
        find_block = find_block.split(")", 1)[0]
        self.assertIn("geographic_msgs", find_block,
                      "find_package(catkin COMPONENTS ...) 必须含 geographic_msgs")
        self.assertIn("catkin_package(",
                      cmake, "CMakeLists.txt 必须含 catkin_package")
        pkg_block = cmake.split("catkin_package(", 1)[1].split(")", 1)[0]
        self.assertIn("geographic_msgs", pkg_block,
                      "catkin_package(CATKIN_DEPENDS ...) 必须含 geographic_msgs")

    def test_group_a_topology_uses_geopointstamped(self):
        text = TOPOLOGY.read_text(encoding="utf-8")
        self.assertIn("geographic_msgs/GeoPointStamped", text)


if __name__ == "__main__":
    unittest.main()
