from builtin_interfaces.msg import Time

from garmin_bridge.app_protocol import (
    UNASSIGNED_SESSION,
    batch_from_json,
    error_response,
    hello_response,
    imu_ack,
    parse_json,
    ping_response,
    validate_envelope,
    validate_imu_batch,
)


def sample_batch(count=25):
    return {
        "type": "imu_batch",
        "version": 1,
        "sequence": 12,
        "watch_timestamp_ms": [1000 + 40 * i for i in range(count)],
        "accel_x_mg": [12.0 + i for i in range(count)],
        "accel_y_mg": [5.0 for _ in range(count)],
        "accel_z_mg": [1000.0 for _ in range(count)],
        "gyro_x_deg_s": [0.1 for _ in range(count)],
        "gyro_y_deg_s": [1.1 for _ in range(count)],
        "gyro_z_deg_s": [0.3 for _ in range(count)],
        "mag_x_mgauss": [300.0 for _ in range(count)],
        "mag_y_mgauss": [10.0 for _ in range(count)],
        "mag_z_mgauss": [-450.0 for _ in range(count)],
        "altitude_m": 251.5,
        "altitude_available": True,
        "phone_receive_time_ns": 1234567890,
    }


def test_valid_hello():
    data, error = parse_json('{"type": "hello", "version": 1, "client": "test_client"}')
    assert error is None
    assert validate_envelope(data) is None
    assert hello_response(data) == {
        "type": "hello_ack",
        "version": 1,
        "server": "wearnav_ros2",
        "recording": False,
        "session_id": "UNASSIGNED",
    }


def test_valid_start_stop_and_ping():
    for raw, msg_type in [
        ('{"type": "start_session", "version": 1, "label": "walk"}', "start_session"),
        ('{"type": "stop_session", "version": 1}', "stop_session"),
    ]:
        data, error = parse_json(raw)
        assert error is None
        assert validate_envelope(data) is None
        assert data["type"] == msg_type

    assert ping_response() == {"type": "pong", "version": 1}


def test_unknown_type_returns_error():
    assert error_response("Unsupported message type") == {
        "type": "error",
        "version": 1,
        "message": "Unsupported message type",
    }


def test_unsupported_version_returns_error():
    data, error = parse_json('{"type": "hello", "version": 2}')
    assert error is None
    assert validate_envelope(data) == {
        "type": "error",
        "version": 1,
        "message": "Unsupported protocol version",
    }


def test_batch_validation():
    assert validate_imu_batch(sample_batch())

    empty = sample_batch(0)
    assert not validate_imu_batch(empty)

    mismatched = sample_batch()
    mismatched["gyro_z_deg_s"] = mismatched["gyro_z_deg_s"][:-1]
    assert not validate_imu_batch(mismatched)

    bad_sequence = sample_batch()
    bad_sequence["sequence"] = -1
    assert not validate_imu_batch(bad_sequence)


def test_ros_batch_conversion():
    data = sample_batch()
    stamp = Time(sec=10, nanosec=20)
    batch = batch_from_json(data, UNASSIGNED_SESSION, stamp, "garmin_watch", 987654321)

    assert batch.header.stamp.sec == 10
    assert batch.header.frame_id == "garmin_watch"
    assert batch.session_id == UNASSIGNED_SESSION
    assert batch.sequence == 12
    assert len(batch.watch_timestamp_ms) == 25
    assert batch.watch_timestamp_ms[1] == 1040
    assert batch.accel_x_mg[2] == 14.0
    assert batch.gyro_available is True
    assert len(batch.mag_x_mgauss) == 25
    assert batch.mag_x_mgauss[0] == 300.0
    assert batch.mag_available is True
    assert batch.altitude_m == 251.5
    assert batch.altitude_available is True
    assert batch.phone_receive_time_ns == 1234567890
    assert batch.pi_receive_time_ns == 987654321
    assert imu_ack(batch.sequence) == {"type": "imu_batch_ack", "version": 1, "sequence": 12}


def test_ros_batch_conversion_defaults_when_fields_missing():
    data = sample_batch()
    del data["altitude_available"]
    stamp = Time(sec=10, nanosec=20)
    batch = batch_from_json(data, UNASSIGNED_SESSION, stamp, "garmin_watch", 987654321)

    # A client with a real magnetometer that simply omits the flag is
    # assumed to have one (matches gyro_available's default), but altitude
    # is assumed unavailable unless a client explicitly says otherwise.
    assert batch.mag_available is True
    assert batch.altitude_available is False
