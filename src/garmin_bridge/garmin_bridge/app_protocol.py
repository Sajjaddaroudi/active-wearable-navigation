import json

from wearnav_interfaces.msg import GarminImuBatch


PROTOCOL_VERSION = 1
SERVER_NAME = "wearnav_ros2"
UNASSIGNED_SESSION = "UNASSIGNED"

IMU_FIELDS = (
    "watch_timestamp_ms",
    "accel_x_mg",
    "accel_y_mg",
    "accel_z_mg",
    "gyro_x_deg_s",
    "gyro_y_deg_s",
    "gyro_z_deg_s",
    "mag_x_mgauss",
    "mag_y_mgauss",
    "mag_z_mgauss",
)


def error_response(message):
    return {"type": "error", "version": PROTOCOL_VERSION, "message": message}


def parse_json(raw):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, error_response("Invalid JSON")
    if not isinstance(data, dict):
        return None, error_response("Invalid JSON")
    return data, None


def validate_envelope(data):
    if data.get("version") != PROTOCOL_VERSION:
        return error_response("Unsupported protocol version")
    if not isinstance(data.get("type"), str):
        return error_response("Invalid message type")
    return None


def hello_response(data, recording=False, session_id=UNASSIGNED_SESSION):
    response = {
        "type": "hello_ack",
        "version": PROTOCOL_VERSION,
        "server": SERVER_NAME,
        "recording": bool(recording),
        "session_id": session_id or UNASSIGNED_SESSION,
    }
    return response


def ping_response():
    return {"type": "pong", "version": PROTOCOL_VERSION}


def validate_imu_batch(data):
    sequence = data.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        return False

    lengths = []
    for field in IMU_FIELDS:
        values = data.get(field)
        if not isinstance(values, list) or not values:
            return False
        lengths.append(len(values))

    return len(set(lengths)) == 1


def batch_from_json(data, session_id, stamp, frame_id, pi_receive_time_ns):
    batch = GarminImuBatch()
    batch.header.stamp = stamp
    batch.header.frame_id = frame_id
    batch.session_id = session_id or UNASSIGNED_SESSION
    batch.sequence = data["sequence"]

    batch.watch_timestamp_ms = [int(v) for v in data["watch_timestamp_ms"]]
    batch.accel_x_mg = [float(v) for v in data["accel_x_mg"]]
    batch.accel_y_mg = [float(v) for v in data["accel_y_mg"]]
    batch.accel_z_mg = [float(v) for v in data["accel_z_mg"]]
    batch.gyro_x_deg_s = [float(v) for v in data["gyro_x_deg_s"]]
    batch.gyro_y_deg_s = [float(v) for v in data["gyro_y_deg_s"]]
    batch.gyro_z_deg_s = [float(v) for v in data["gyro_z_deg_s"]]
    # Older/other clients that don't send this field are assumed to have a
    # real gyroscope (the pre-existing behavior), so evaluate_imu's
    # gyroscope check still fires normally for them.
    batch.gyro_available = bool(data.get("gyro_available", True))

    batch.mag_x_mgauss = [float(v) for v in data["mag_x_mgauss"]]
    batch.mag_y_mgauss = [float(v) for v in data["mag_y_mgauss"]]
    batch.mag_z_mgauss = [float(v) for v in data["mag_z_mgauss"]]
    batch.mag_available = bool(data.get("mag_available", True))

    batch.altitude_m = float(data.get("altitude_m", 0.0))
    batch.altitude_available = bool(data.get("altitude_available", False))

    batch.phone_receive_time_ns = int(data.get("phone_receive_time_ns", 0))
    batch.pi_receive_time_ns = pi_receive_time_ns
    return batch


def imu_ack(sequence):
    return {"type": "imu_batch_ack", "version": PROTOCOL_VERSION, "sequence": sequence}
