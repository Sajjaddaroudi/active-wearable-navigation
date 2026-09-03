import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from wearnav_interfaces.msg import GarminImuBatch


class FakeGarminPublisher(Node):
    def __init__(self):
        super().__init__("fake_garmin_publisher")
        self.declare_parameter("sample_rate_hz", 25.0)
        self.declare_parameter("batch_period_s", 1.0)
        self.declare_parameter("frame_id", "garmin_watch")

        self.sample_rate_hz = float(self.get_parameter("sample_rate_hz").value)
        self.batch_period_s = float(self.get_parameter("batch_period_s").value)
        self.frame_id = str(self.get_parameter("frame_id").value)

        self.samples_per_batch = max(1, round(self.sample_rate_hz * self.batch_period_s))
        self.sequence = 0
        self.sample_index = 0
        self.watch_time_ms = 0

        self.pub = self.create_publisher(
            GarminImuBatch, "/wearnav/garmin/imu_raw", qos_profile_sensor_data
        )
        self.timer = self.create_timer(self.batch_period_s, self.publish_batch)
        self.get_logger().info("Publishing simulated Garmin IMU data")

    def publish_batch(self):
        batch = GarminImuBatch()
        batch.header.stamp = self.get_clock().now().to_msg()
        batch.header.frame_id = self.frame_id
        batch.sequence = self.sequence
        batch.gyro_available = True
        batch.mag_available = True
        # Simulate a slow walk up a gentle incline so altitude isn't flat.
        batch.altitude_available = True
        batch.altitude_m = 250.0 + 0.05 * self.sequence
        batch.pi_receive_time_ns = self.get_clock().now().nanoseconds

        step_ms = round(1000.0 / self.sample_rate_hz)
        for _ in range(self.samples_per_batch):
            t = self.sample_index / self.sample_rate_hz
            phase = 2.0 * math.pi * 1.6 * t
            # A slower phase to simulate heading drifting as the wearer walks.
            heading_phase = 2.0 * math.pi * 0.05 * t

            batch.watch_timestamp_ms.append(self.watch_time_ms)
            batch.accel_x_mg.append(55.0 * math.sin(phase))
            batch.accel_y_mg.append(20.0 * math.sin(0.5 * phase))
            batch.accel_z_mg.append(1000.0 + 80.0 * math.sin(phase + 0.4))
            batch.gyro_x_deg_s.append(8.0 * math.sin(phase + 0.2))
            batch.gyro_y_deg_s.append(4.0 * math.sin(0.7 * phase))
            batch.gyro_z_deg_s.append(12.0 * math.sin(phase + 1.0))
            # Earth's field is roughly 250-650 mGauss; wobble it slowly to
            # simulate the wearer's heading changing.
            batch.mag_x_mgauss.append(300.0 * math.cos(heading_phase))
            batch.mag_y_mgauss.append(300.0 * math.sin(heading_phase))
            batch.mag_z_mgauss.append(-450.0)

            self.watch_time_ms += step_ms
            self.sample_index += 1

        lengths = {
            len(batch.watch_timestamp_ms),
            len(batch.accel_x_mg),
            len(batch.accel_y_mg),
            len(batch.accel_z_mg),
            len(batch.gyro_x_deg_s),
            len(batch.gyro_y_deg_s),
            len(batch.gyro_z_deg_s),
            len(batch.mag_x_mgauss),
            len(batch.mag_y_mgauss),
            len(batch.mag_z_mgauss),
        }
        if len(lengths) != 1:
            self.get_logger().warning("Skipping malformed simulated Garmin batch")
            return

        self.pub.publish(batch)
        self.sequence += 1


def main(args=None):
    rclpy.init(args=args)
    node = FakeGarminPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
