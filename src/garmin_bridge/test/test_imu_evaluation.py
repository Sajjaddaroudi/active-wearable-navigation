import math
from types import SimpleNamespace

from garmin_bridge.imu_evaluation import evaluate_batches


def make_batch(sequence, sample_rate_hz=25.0, gyro_peak=20.0):
    count = 25
    step_ms = round(1000.0 / sample_rate_hz)
    phase_offset = sequence * count
    indexes = range(count)
    return SimpleNamespace(
        sequence=sequence,
        watch_timestamp_ms=[sequence * 1000 + i * step_ms for i in indexes],
        accel_x_mg=[300.0 * math.sin((phase_offset + i) * 0.1) for i in indexes],
        accel_y_mg=[100.0 * math.cos((phase_offset + i) * 0.1) for i in indexes],
        accel_z_mg=[950.0 for _ in indexes],
        gyro_x_deg_s=[gyro_peak * math.sin((phase_offset + i) * 0.2) for i in indexes],
        gyro_y_deg_s=[2.0 for _ in indexes],
        gyro_z_deg_s=[1.0 for _ in indexes],
    )


def arrival_times(count):
    return [1_000_000_000 * i for i in range(count)]


def test_accepts_moving_physical_watch_data():
    batches = [make_batch(i) for i in range(6)]
    report = evaluate_batches(
        batches, arrival_times(len(batches)), ["app_command_bridge"]
    )

    assert report.passed
    assert report.statistics["samples"] == 150
    assert report.statistics["sample_rate_hz"] == 25.0
    assert report.statistics["gyro_peak_deg_s"] > 19.0


def test_rejects_fake_publisher():
    batches = [make_batch(i) for i in range(6)]
    report = evaluate_batches(
        batches, arrival_times(len(batches)), ["fake_garmin_publisher"]
    )

    assert not report.passed
    assert any(check.name == "source" and check.status == "FAIL" for check in report.checks)


def test_rejects_accelerometer_only_fallback():
    batches = [make_batch(i, gyro_peak=0.0) for i in range(6)]
    for batch in batches:
        batch.gyro_y_deg_s = [0.0] * 25
        batch.gyro_z_deg_s = [0.0] * 25

    report = evaluate_batches(
        batches, arrival_times(len(batches)), ["app_command_bridge"]
    )

    assert not report.passed
    assert any(
        check.name == "gyroscope" and check.status == "FAIL"
        for check in report.checks
    )


def test_rejects_wrong_sample_rate_and_malformed_batch():
    batches = [make_batch(i, sample_rate_hz=10.0) for i in range(6)]
    batches[2].gyro_z_deg_s.pop()
    report = evaluate_batches(
        batches, arrival_times(len(batches)), ["app_command_bridge"]
    )

    assert not report.passed
    assert any(
        check.name == "batch integrity" and check.status == "FAIL"
        for check in report.checks
    )
    assert any(
        check.name == "sample rate" and check.status == "FAIL"
        for check in report.checks
    )
