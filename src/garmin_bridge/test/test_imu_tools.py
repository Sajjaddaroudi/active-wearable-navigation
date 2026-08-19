from math import isclose, pi
from types import SimpleNamespace

from garmin_bridge.imu_tools import deg_s_to_rad_s, mg_to_ms2, relative_sample_times, valid_batch


def batch(stamps=(1000, 1040, 1080)):
    values = [0.0] * len(stamps)
    return SimpleNamespace(
        watch_timestamp_ms=list(stamps),
        accel_x_mg=values,
        accel_y_mg=values,
        accel_z_mg=values,
        gyro_x_deg_s=values,
        gyro_y_deg_s=values,
        gyro_z_deg_s=values,
    )


def test_unit_conversions():
    assert isclose(mg_to_ms2(1000.0), 9.80665)
    assert isclose(deg_s_to_rad_s(180.0), pi)


def test_rejects_mismatched_lengths():
    msg = batch()
    msg.gyro_z_deg_s = [0.0]
    assert not valid_batch(msg)


def test_relative_times_are_monotonic():
    times = relative_sample_times(batch(), 5_000_000_000)
    assert times == [5_000_000_000, 5_040_000_000, 5_080_000_000]
    assert times[0] < times[1] < times[2]

