import math
import statistics
from dataclasses import dataclass

from garmin_bridge.imu_tools import batch_length


IMU_VALUE_FIELDS = (
    "accel_x_mg",
    "accel_y_mg",
    "accel_z_mg",
    "gyro_x_deg_s",
    "gyro_y_deg_s",
    "gyro_z_deg_s",
)


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


@dataclass
class EvaluationReport:
    passed: bool
    checks: list
    statistics: dict


def _finite(values):
    return all(math.isfinite(float(value)) for value in values)


def _vector_magnitudes(x, y, z):
    return [
        math.sqrt(float(a) ** 2 + float(b) ** 2 + float(c) ** 2)
        for a, b, c in zip(x, y, z)
    ]


def _publisher_check(publisher_names):
    names = {name.lstrip("/") for name in publisher_names}
    if "fake_garmin_publisher" in names:
        return CheckResult(
            "source",
            "FAIL",
            "raw topic is published by fake_garmin_publisher, not the watch bridge",
        )
    if "app_command_bridge" in names:
        return CheckResult(
            "source", "PASS", "raw topic is published by app_command_bridge"
        )
    if names:
        return CheckResult(
            "source",
            "WARN",
            "publisher is " + ", ".join(sorted(names)) + "; source is not verified",
        )
    return CheckResult("source", "WARN", "no publisher identity was discovered")


def evaluate_batches(
    batches,
    arrival_times_ns,
    publisher_names=(),
    expected_sample_rate_hz=25.0,
    minimum_batches=5,
    minimum_gyro_peak_deg_s=5.0,
    offline=False,
):
    if offline:
        checks = [
            CheckResult(
                "recording",
                "PASS",
                "raw IMU batches were read directly from the saved rosbag",
            ),
            CheckResult(
                "source provenance",
                "WARN",
                "a rosbag does not retain enough publisher identity to prove "
                "that samples came from a physical watch",
            ),
        ]
    else:
        checks = [_publisher_check(publisher_names)]
    stats = {
        "batches": len(batches),
        "samples": 0,
        "sample_rate_hz": 0.0,
        "batch_rate_hz": 0.0,
        "accel_median_mg": 0.0,
        "accel_min_mg": 0.0,
        "accel_max_mg": 0.0,
        "gyro_peak_deg_s": 0.0,
        "sequence_gaps": 0,
    }

    if len(batches) < minimum_batches:
        checks.append(
            CheckResult(
                "batch count",
                "FAIL",
                f"received {len(batches)} batches; need at least {minimum_batches}",
            )
        )
    else:
        checks.append(
            CheckResult("batch count", "PASS", f"received {len(batches)} batches")
        )

    valid_batches = []
    malformed = 0
    all_finite = True
    timestamp_steps_ms = []
    for batch in batches:
        count = batch_length(batch)
        if not count:
            malformed += 1
            continue
        stamps = list(batch.watch_timestamp_ms)
        steps = [stamps[i] - stamps[i - 1] for i in range(1, len(stamps))]
        # A tie (step == 0) is coarse millisecond timestamp resolution on
        # real watch hardware, not corrupted data - only a reversal
        # (negative step) indicates an actual problem. Keep in sync with
        # imu_tools.valid_batch's tolerance.
        if any(step < 0 for step in steps):
            malformed += 1
            continue
        if not all(_finite(getattr(batch, field)) for field in IMU_VALUE_FIELDS):
            all_finite = False
            continue
        valid_batches.append(batch)
        timestamp_steps_ms.extend(steps)
        stats["samples"] += count

    if malformed or not all_finite:
        detail = f"{malformed} malformed batches"
        if not all_finite:
            detail += "; non-finite sensor values found"
        checks.append(CheckResult("batch integrity", "FAIL", detail))
    elif valid_batches:
        checks.append(
            CheckResult(
                "batch integrity",
                "PASS",
                "array lengths match; timestamps increase; values are finite",
            )
        )
    else:
        checks.append(CheckResult("batch integrity", "FAIL", "no valid batches"))

    if timestamp_steps_ms:
        median_step_ms = statistics.median(timestamp_steps_ms)
        stats["sample_rate_hz"] = 1000.0 / median_step_ms
        tolerance = expected_sample_rate_hz * 0.20
        if abs(stats["sample_rate_hz"] - expected_sample_rate_hz) <= tolerance:
            checks.append(
                CheckResult(
                    "sample rate",
                    "PASS",
                    f"{stats['sample_rate_hz']:.2f} Hz (median step {median_step_ms:.1f} ms)",
                )
            )
        else:
            checks.append(
                CheckResult(
                    "sample rate",
                    "FAIL",
                    f"{stats['sample_rate_hz']:.2f} Hz; expected about "
                    f"{expected_sample_rate_hz:.1f} Hz",
                )
            )
    else:
        checks.append(CheckResult("sample rate", "FAIL", "no timestamp steps"))

    sequences = [int(batch.sequence) for batch in valid_batches]
    gaps = sum(
        max(0, current - previous - 1)
        for previous, current in zip(sequences, sequences[1:])
    )
    stats["sequence_gaps"] = gaps
    if gaps:
        checks.append(
            CheckResult("sequence", "WARN", f"{gaps} batches were dropped in transport")
        )
    elif sequences:
        checks.append(CheckResult("sequence", "PASS", "batch sequence is continuous"))
    else:
        checks.append(CheckResult("sequence", "FAIL", "no valid sequence values"))

    if len(arrival_times_ns) >= 2:
        elapsed_s = (arrival_times_ns[-1] - arrival_times_ns[0]) / 1_000_000_000.0
        if elapsed_s > 0:
            stats["batch_rate_hz"] = (len(arrival_times_ns) - 1) / elapsed_s
            if 0.5 <= stats["batch_rate_hz"] <= 1.5:
                checks.append(
                    CheckResult(
                        "batch cadence", "PASS", f"{stats['batch_rate_hz']:.2f} batches/s"
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        "batch cadence",
                        "WARN",
                        f"{stats['batch_rate_hz']:.2f} batches/s; expected about 1",
                    )
                )

    accel_magnitudes = []
    gyro_magnitudes = []
    for batch in valid_batches:
        accel_magnitudes.extend(
            _vector_magnitudes(
                batch.accel_x_mg, batch.accel_y_mg, batch.accel_z_mg
            )
        )
        gyro_magnitudes.extend(
            _vector_magnitudes(
                batch.gyro_x_deg_s, batch.gyro_y_deg_s, batch.gyro_z_deg_s
            )
        )

    if accel_magnitudes:
        stats["accel_median_mg"] = statistics.median(accel_magnitudes)
        stats["accel_min_mg"] = min(accel_magnitudes)
        stats["accel_max_mg"] = max(accel_magnitudes)
        if 500.0 <= stats["accel_median_mg"] <= 1500.0:
            checks.append(
                CheckResult(
                    "accelerometer",
                    "PASS",
                    f"median magnitude {stats['accel_median_mg']:.1f} mg "
                    "(gravity is about 1000 mg)",
                )
            )
        else:
            checks.append(
                CheckResult(
                    "accelerometer",
                    "FAIL",
                    f"median magnitude {stats['accel_median_mg']:.1f} mg is implausible",
                )
            )
    else:
        checks.append(CheckResult("accelerometer", "FAIL", "no accelerometer data"))

    # A watch with no gyroscope hardware (e.g. Forerunner 165) correctly
    # reports gyro_available=False and sends zero-filled gyro arrays for
    # transport compatibility. That's an expected device limitation, not a
    # recording defect, so it should not fail the trial the way a
    # gyro-equipped watch producing suspiciously flat data would.
    gyro_hardware_available = any(
        getattr(batch, "gyro_available", True) for batch in valid_batches
    ) if valid_batches else True

    if gyro_magnitudes:
        stats["gyro_peak_deg_s"] = max(gyro_magnitudes)
        if not gyro_hardware_available and stats["gyro_peak_deg_s"] < minimum_gyro_peak_deg_s:
            checks.append(
                CheckResult(
                    "gyroscope",
                    "WARN",
                    "device reports no gyroscope hardware; accelerometer-only trial",
                )
            )
        elif stats["gyro_peak_deg_s"] >= minimum_gyro_peak_deg_s:
            checks.append(
                CheckResult(
                    "gyroscope",
                    "PASS",
                    f"motion detected; peak {stats['gyro_peak_deg_s']:.2f} deg/s",
                )
            )
        else:
            checks.append(
                CheckResult(
                    "gyroscope",
                    "FAIL",
                    f"peak is only {stats['gyro_peak_deg_s']:.2f} deg/s; "
                    "rotate the watch during the test",
                )
            )
    else:
        checks.append(CheckResult("gyroscope", "FAIL", "no gyroscope data"))

    passed = not any(check.status == "FAIL" for check in checks)
    return EvaluationReport(passed, checks, stats)
