from sensor_msgs.msg import Imu

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from garmin_bridge.imu_tools import (
    deg_s_to_rad_s,
    mg_to_ms2,
    relative_sample_times,
    valid_batch,
)
from wearnav_interfaces.msg import GarminImuBatch


class GarminImuConverter(Node):
    def __init__(self):
        super().__init__("garmin_imu_converter")
        self.declare_parameter("frame_id", "garmin_watch")
        self.frame_id = str(self.get_parameter("frame_id").value)

        self.pub = self.create_publisher(
            Imu, "/wearnav/garmin/imu", qos_profile_sensor_data
        )
        self.sub = self.create_subscription(
            GarminImuBatch,
            "/wearnav/garmin/imu_raw",
            self.convert_batch,
            qos_profile_sensor_data,
        )

    def convert_batch(self, batch):
        if not valid_batch(batch):
            self.get_logger().warning("Ignoring malformed Garmin IMU batch")
            return

        # Batch arrival is the anchor until the phone/watch clock sync is known.
        anchor_ns = self.get_clock().now().nanoseconds
        for i, stamp_ns in enumerate(relative_sample_times(batch, anchor_ns)):
            imu = Imu()
            imu.header.stamp = rclpy.time.Time(nanoseconds=stamp_ns).to_msg()
            imu.header.frame_id = batch.header.frame_id or self.frame_id
            imu.orientation_covariance[0] = -1.0

            imu.linear_acceleration.x = mg_to_ms2(batch.accel_x_mg[i])
            imu.linear_acceleration.y = mg_to_ms2(batch.accel_y_mg[i])
            imu.linear_acceleration.z = mg_to_ms2(batch.accel_z_mg[i])
            imu.angular_velocity.x = deg_s_to_rad_s(batch.gyro_x_deg_s[i])
            imu.angular_velocity.y = deg_s_to_rad_s(batch.gyro_y_deg_s[i])
            imu.angular_velocity.z = deg_s_to_rad_s(batch.gyro_z_deg_s[i])
            self.pub.publish(imu)


def main(args=None):
    rclpy.init(args=args)
    node = GarminImuConverter()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

