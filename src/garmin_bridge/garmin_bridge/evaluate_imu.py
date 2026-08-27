import argparse
import math
from pathlib import Path

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

from garmin_bridge.imu_evaluation import evaluate_batches
from garmin_bridge.imu_tools import batch_length


TOPIC = "/wearnav/garmin/imu_raw"


def resolve_bag_directory(trial_path):
    path = Path(trial_path).expanduser().resolve()
    candidates = []

    if path.is_dir():
        candidates.extend((path / "bag", path))
    elif path.name == "metadata.yaml":
        candidates.append(path.parent)
    elif path.suffix == ".db3":
        candidates.append(path.parent)

    for candidate in candidates:
        if (candidate / "metadata.yaml").is_file():
            return candidate

    raise FileNotFoundError(
        f"no rosbag2 metadata.yaml found for trial path: {trial_path}"
    )


def read_raw_batches(bag_directory):
    reader = rosbag2_py.SequentialReader()
    storage_options = rosbag2_py.StorageOptions(
        uri=str(bag_directory), storage_id="sqlite3"
    )
    reader.open(storage_options, rosbag2_py.ConverterOptions("", ""))

    topic_types = {
        topic.name: topic.type for topic in reader.get_all_topics_and_types()
    }
    if TOPIC not in topic_types:
        available = ", ".join(sorted(topic_types)) or "none"
        raise RuntimeError(f"{TOPIC} is not in the bag; available topics: {available}")

    message_type = get_message(topic_types[TOPIC])
    batches = []
    record_times_ns = []
    while reader.has_next():
        topic, serialized, record_time_ns = reader.read_next()
        if topic != TOPIC:
            continue
        batches.append(deserialize_message(serialized, message_type))
        record_times_ns.append(record_time_ns)
    return batches, record_times_ns


def print_batch(batch, show_samples=False):
    count = batch_length(batch)
    if not count:
        print(f"batch seq={batch.sequence}: MALFORMED")
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
        f"gyro_peak={gyro_peak:8.2f} deg/s"
    )

    if show_samples:
        for index in range(count):
            print(
                f"  {batch.watch_timestamp_ms[index]} ms "
                f"a=({batch.accel_x_mg[index]:.1f}, "
                f"{batch.accel_y_mg[index]:.1f}, "
                f"{batch.accel_z_mg[index]:.1f}) mg "
                f"g=({batch.gyro_x_deg_s[index]:.2f}, "
                f"{batch.gyro_y_deg_s[index]:.2f}, "
                f"{batch.gyro_z_deg_s[index]:.2f}) deg/s"
            )


def print_report(report, bag_directory):
    print("\nWearNav offline IMU evaluation")
    print(f"trial: {bag_directory.parent}")
    print(f"bag:   {bag_directory}")
    print("=" * 56)
    for check in report.checks:
        print(f"[{check.status:4}] {check.name}: {check.detail}")

    stats = report.statistics
    print("-" * 56)
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
    print("=" * 56)
    if report.passed:
        print("RESULT: PASS - recorded six-axis IMU data looks valid")
    else:
        print("RESULT: FAIL - see failed checks above")


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Evaluate one recorded WearNav session offline."
    )
    parser.add_argument(
        "trial",
        help="session directory, bag directory, metadata.yaml, or bag .db3 file",
    )
    parser.add_argument(
        "--expected-rate",
        type=float,
        default=25.0,
        help="expected watch sample rate in Hz (default: 25)",
    )
    parser.add_argument(
        "--minimum-batches",
        type=int,
        default=5,
        help="minimum number of raw batches required (default: 5)",
    )
    parser.add_argument(
        "--minimum-gyro-peak",
        type=float,
        default=5.0,
        help="minimum rotation peak in deg/s (default: 5)",
    )
    parser.add_argument(
        "--show-samples",
        action="store_true",
        help="print every sample instead of one summary line per batch",
    )
    return parser.parse_args(args)


def main(args=None):
    options = parse_args(args)
    try:
        bag_directory = resolve_bag_directory(options.trial)
        batches, record_times_ns = read_raw_batches(bag_directory)
    except (FileNotFoundError, RuntimeError) as error:
        print(f"ERROR: {error}")
        return 2

    print(f"Reading recorded trial: {bag_directory.parent}")
    print(f"Found {len(batches)} raw IMU batches on {TOPIC}.\n")
    for batch in batches:
        print_batch(batch, options.show_samples)

    report = evaluate_batches(
        batches,
        record_times_ns,
        publisher_names=(),
        expected_sample_rate_hz=options.expected_rate,
        minimum_batches=options.minimum_batches,
        minimum_gyro_peak_deg_s=options.minimum_gyro_peak,
        offline=True,
    )
    print_report(report, bag_directory)
    return 0 if report.passed else 1
