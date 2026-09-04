import os
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

RECORDED_TOPICS = [
    "/wearnav/garmin/imu_raw",
    "/wearnav/garmin/imu",
    "/wearnav/ble/rssi_raw",
    "/wearnav/session/state",
]

# Topics fed directly by an external bridge (phone -> app_command_bridge),
# where the very first message can race the rosbag2 recorder's DDS discovery
# and be silently lost if we don't wait for it. Deliberately NOT every
# RECORDED_TOPICS entry: /wearnav/garmin/imu is a *derived* topic - its
# publisher (garmin_imu_converter) exists from node startup regardless of
# whether any data has flowed yet, so a generic "does this topic have a
# live publisher" check sweeps it in too, waiting on a DDS match that isn't
# protecting against the same kind of loss (converted samples keep arriving
# continuously as long as imu_raw does) and just adds an extra match to the
# same timeout window. This list is deliberately explicit rather than
# derived, so adding a future processing/derived topic to RECORDED_TOPICS
# doesn't silently widen what start_session blocks on.
RAW_INPUT_TOPICS = [
    "/wearnav/garmin/imu_raw",
    "/wearnav/ble/rssi_raw",
]


def sanitize_label(label):
    label = re.sub(r"[^A-Za-z0-9]+", "_", label.strip().lower()).strip("_")
    return label or "session"


def make_session_id(label, data_root, now=None):
    now = now or datetime.now()
    prefix = now.strftime("%Y%m%d_%H%M%S")
    clean = sanitize_label(label)
    for index in range(1, 1000):
        session_id = f"{prefix}_{clean}_{index:03d}"
        if not (Path(data_root) / session_id).exists():
            return session_id
    raise RuntimeError("could not allocate a session id")


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def git_commit(repo_root):
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def os_version():
    try:
        return subprocess.check_output(["lsb_release", "-ds"], text=True).strip()
    except subprocess.CalledProcessError:
        return platform.platform()


def base_metadata(session_id, label, repo_root, params):
    return {
        "session_id": session_id,
        "label": label,
        "start_time": iso_now(),
        "end_time": None,
        "duration": None,
        "hostname": platform.node(),
        "os_version": os_version(),
        "architecture": platform.machine(),
        "ros_distro": os.environ.get("ROS_DISTRO", "unknown"),
        "git_commit": git_commit(repo_root),
        "recorded_topics": RECORDED_TOPICS,
        "sample_rate_hz": params["sample_rate_hz"],
        "batch_period_s": params["batch_period_s"],
        "frame_id": params["frame_id"],
        "status": "recording",
    }


def write_metadata(path, metadata):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)

