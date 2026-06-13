#!/usr/bin/env python3
"""Compatibility bridge for older Twist teleop tools.

The ROSbot Jazzy controller consumes geometry_msgs/TwistStamped on cmd_vel.
Many teleop tools still publish geometry_msgs/Twist by default. This bridge
accepts the older message and republishes a stamped command for the controller.
"""

import argparse

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException


class TwistCompatBridge(Node):
    def __init__(self, namespace: str, frame_id: str, in_topic: str, out_topic: str) -> None:
        node_name = "rosbot_twist_compat_bridge"
        super().__init__(node_name, namespace=namespace)
        self._frame_id = frame_id
        self._publisher = self.create_publisher(TwistStamped, out_topic, 10)
        self._subscription = self.create_subscription(Twist, in_topic, self._on_twist, 10)

    def _on_twist(self, msg: Twist) -> None:
        stamped = TwistStamped()
        stamped.header.stamp = self.get_clock().now().to_msg()
        stamped.header.frame_id = self._frame_id
        stamped.twist = msg
        self._publisher.publish(stamped)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge Twist cmd_vel commands to TwistStamped.")
    parser.add_argument("--namespace", default="", help="ROS namespace without leading slash")
    parser.add_argument("--frame-id", default="base_link", help="Frame id for stamped velocity commands")
    parser.add_argument("--in-topic", default="cmd_vel", help="Twist input topic")
    parser.add_argument("--out-topic", default="cmd_vel_stamped", help="TwistStamped output topic")
    args = parser.parse_args()

    namespace = args.namespace.strip("/")

    rclpy.init()
    node = TwistCompatBridge(
        namespace=namespace,
        frame_id=args.frame_id,
        in_topic=args.in_topic,
        out_topic=args.out_topic,
    )
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
