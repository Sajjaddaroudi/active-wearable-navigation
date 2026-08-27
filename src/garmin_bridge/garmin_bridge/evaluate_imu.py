import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from garmin_bridge.imu_evaluation import evaluate_batches
from garmin_bridge.imu_tools import batch_length
from wearnav_interfaces.msg import GarminImuBatch


TOPIC = "/wearnav/garmin/imu_raw"


class ImuEvaluationNode(Node):
    def __init__(self):
        super().__init__("wearnav_imu_evaluator")
        self.declare_parameter("duration_s", 15.0)
        self.declare_parameter("expected_sample_rate_hz", 25.0)
        self.declare_parameter("minimum_batches", 5)
        self.declare_parameter("minimum_gyro_peak_deg_s", 5.0)
        self.declare_parameter("show_samples", False)

        self.duration_s = float(self.get_parameter("duration_s").value)
        self.expected_sample_rate_hz = float(
            self.get_parameter("expected_sample_rate_hz").value
        )
        self.minimum_batches = int(self.get_parameter("minimum_batches").value)
        self.minimum_gyro_peak_deg_s = float(
            self.get_parameter("minimum_gyro_peak_deg_s").value
        )
        self.show_samples = bool(self.get_parameter("show_samples").value)
        self.batches = []
        self.arrival_times_ns = []
        self.publisher_names = set()

        self.subscription = self.create_subscription(
            GarminImuBatch, TOPIC, self.on_batch, qos_profile_sensor_data
        )

    def discover_publishers(self):
        for info in self.get_publishers_info_by_topic(TOPIC):
            self.publisher_names.add(info.node_name)

    def on_batch(self, batch):
        self.batches.append(batch)
        self.arrival_times_ns.append(time.monotonic_ns())
        self.discover_publishers()

        count = batch_length(batch)
        if not count:
            print(f"batch seq={batch.sequence}: MALFORMED", flush=True)
            return

        accel_magnitude = math.sqrt(
            batch.accel_x_mg[0] ** 2
            + batch.accel_y_mg[0] ** 2
            + batch.accel_z_mg[0] ** 2
        )
        gyro_peak = max(
            math.sqrt(x**2 + y**2 + z**2)
            for x, y, z in zip(
                batch.gyro_x_deg_s,
                batch.gyro_y_deg_s,
                batch.gyro_z_deg_s,
            )
        )
        print(
            f"batch seq={batch.sequence:<6} samples={count:<3} "
            f"a0=({batch.accel_x_mg[0]:8.1f}, {batch.accel_y_mg[0]:8.1f}, "
            f"{batch.accel_z_mg[0]:8.1f}) mg |a0|={accel_magnitude:7.1f} mg "
            f"gyro_peak={gyro_peak:8.2f} deg/s",
            flush=True,
        )

        if self.show_samples:
            for index in range(count):
                print(
                    f"  {batch.watch_timestamp_ms[index]} ms "
                    f"a=({batch.accel_x_mg[index]:.1f}, "
                    f"{batch.accel_y_mg[index]:.1f}, "
                    f"{batch.accel_z_mg[index]:.1f}) mg "
                    f"g=({batch.gyro_x_deg_s[index]:.2f}, "
                    f"{batch.gyro_y_deg_s[index]:.2f}, "
                    f"{batch.gyro_z_deg_s[index]:.2f}) deg/s",
                    flush=True,
                )


def _print_report(report):
    print("\nWearNav IMU evaluation")
    print("=" * 48)
    for check in report.checks:
        print(f"[{check.status:4}] {check.name}: {check.detail}")

    stats = report.statistics
    print("-" * 48)
    print(f"batches:              {stats['batches']}")
    print(f"samples:              {stats['samples']}")
    print(f"sample rate:          {stats['sample_rate_hz']:.2f} Hz")
    print(f"batch rate:           {stats['batch_rate_hz']:.2f} Hz")
    print(f"accel median:         {stats['accel_median_mg']:.1f} mg")
    print(
        f"accel range:          {stats['accel_min_mg']:.1f} .. "
        f"{stats['accel_max_mg']:.1f} mg"
    )
    print(f"gyro peak:            {stats['gyro_peak_deg_s']:.2f} deg/s")
    print(f"transport gaps:       {stats['sequence_gaps']}")
    print("=" * 48)
    if report.passed:
        print("RESULT: PASS - physical six-axis IMU data looks valid")
    else:
        print("RESULT: FAIL - see failed checks above")


def main(args=None):
    rclpy.init(args=args)
    node = ImuEvaluationNode()
    print(f"Listening to {TOPIC} for {node.duration_s:.1f} seconds.")
    print("Keep the watch still briefly, then rotate it around several axes.\n")

    deadline = time.monotonic() + node.duration_s
    try:
        while rclpy.ok() and time.monotonic() < deadline:
            node.discover_publishers()
            rclpy.spin_once(node, timeout_sec=0.25)
    except KeyboardInterrupt:
        print("\nEvaluation stopped early.")

    report = evaluate_batches(
        node.batches,
        node.arrival_times_ns,
        node.publisher_names,
        node.expected_sample_rate_hz,
        node.minimum_batches,
        node.minimum_gyro_peak_deg_s,
    )
    _print_report(report)
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    return 0 if report.passed else 1
