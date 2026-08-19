from math import pi

MG_TO_MS2 = 9.80665 / 1000.0
DEG_TO_RAD = pi / 180.0


def mg_to_ms2(value):
    return value * MG_TO_MS2


def deg_s_to_rad_s(value):
    return value * DEG_TO_RAD


def batch_length(batch):
    lengths = [
        len(batch.watch_timestamp_ms),
        len(batch.accel_x_mg),
        len(batch.accel_y_mg),
        len(batch.accel_z_mg),
        len(batch.gyro_x_deg_s),
        len(batch.gyro_y_deg_s),
        len(batch.gyro_z_deg_s),
    ]
    if not lengths or len(set(lengths)) != 1:
        return None
    return lengths[0]


def valid_batch(batch):
    count = batch_length(batch)
    if not count:
        return False
    stamps = batch.watch_timestamp_ms
    return all(stamps[i] > stamps[i - 1] for i in range(1, len(stamps)))


def relative_sample_times(batch, anchor_time):
    first_ms = batch.watch_timestamp_ms[0]
    times = []
    for stamp_ms in batch.watch_timestamp_ms:
        dt_ns = int(stamp_ms - first_ms) * 1_000_000
        times.append(anchor_time + dt_ns)
    return times

