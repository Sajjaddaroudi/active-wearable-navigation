import os
import signal
import subprocess
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from wearnav_interfaces.msg import SessionState
from wearnav_interfaces.srv import StartSession, StopSession
from wearnav_recorder.session_utils import (
    RECORDED_TOPICS,
    base_metadata,
    make_session_id,
    sanitize_label,
    write_metadata,
)


class SessionManager(Node):
    def __init__(self):
        super().__init__("session_manager")
        self.declare_parameter("data_root", "")
        self.declare_parameter("sample_rate_hz", 25.0)
        self.declare_parameter("batch_period_s", 1.0)
        self.declare_parameter("frame_id", "garmin_watch")

        data_root = str(self.get_parameter("data_root").value)
        if data_root:
            self.data_root = Path(data_root).expanduser()
        else:
            self.data_root = Path.home() / "wearnav_data"
        self.repo_root = Path(__file__).resolve().parents[3]

        self.recording = False
        self.session_id = ""
        self.label = ""
        self.session_dir = None
        self.metadata = None
        self.start_time = None
        self.bag_process = None

        qos = QoSProfile(depth=1)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.state_pub = self.create_publisher(SessionState, "/wearnav/session/state", qos)
        self.start_srv = self.create_service(
            StartSession, "/wearnav/session/start", self.start_session
        )
        self.stop_srv = self.create_service(
            StopSession, "/wearnav/session/stop", self.stop_session
        )
        self.publish_state("idle")

    def start_session(self, request, response):
        if self.recording:
            response.success = False
            response.session_id = self.session_id
            response.session_directory = str(self.session_dir)
            response.message = "already recording"
            return response

        self.label = sanitize_label(request.label)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.session_id = make_session_id(self.label, self.data_root)
        self.session_dir = self.data_root / self.session_id
        bag_dir = self.session_dir / "bag"
        self.session_dir.mkdir(parents=True)

        params = {
            "sample_rate_hz": float(self.get_parameter("sample_rate_hz").value),
            "batch_period_s": float(self.get_parameter("batch_period_s").value),
            "frame_id": str(self.get_parameter("frame_id").value),
        }
        self.metadata = base_metadata(self.session_id, self.label, self.repo_root, params)
        write_metadata(self.session_dir / "metadata.yaml", self.metadata)

        cmd = ["ros2", "bag", "record", "-o", str(bag_dir), *RECORDED_TOPICS]
        self.bag_process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(1.0)
        if self.bag_process.poll() is not None:
            self.metadata["status"] = "failed"
            write_metadata(self.session_dir / "metadata.yaml", self.metadata)
            response.success = False
            response.session_id = self.session_id
            response.session_directory = str(self.session_dir)
            response.message = "rosbag2 failed to start"
            return response

        self.recording = True
        self.start_time = time.time()
        self.publish_state("recording")
        response.success = True
        response.session_id = self.session_id
        response.session_directory = str(self.session_dir)
        response.message = "recording started"
        return response

    def stop_session(self, request, response):
        if not self.recording:
            response.success = False
            response.message = "not recording"
            return response

        session_id = self.session_id
        session_dir = self.session_dir
        self._finish_recording("complete")
        response.success = True
        response.session_id = session_id
        response.session_directory = str(session_dir)
        response.message = "recording stopped"
        return response

    def _finish_recording(self, status):
        if self.bag_process and self.bag_process.poll() is None:
            self.bag_process.send_signal(signal.SIGINT)
            try:
                self.bag_process.wait(timeout=8.0)
            except subprocess.TimeoutExpired:
                self.bag_process.terminate()
                self.bag_process.wait(timeout=4.0)

        if self.metadata:
            self.metadata["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if self.start_time:
                self.metadata["duration"] = round(time.time() - self.start_time, 3)
            self.metadata["status"] = status
            write_metadata(self.session_dir / "metadata.yaml", self.metadata)

        self.recording = False
        self.bag_process = None
        self.publish_state("idle")

    def publish_state(self, status):
        msg = SessionState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.session_id = self.session_id
        msg.label = self.label
        msg.recording = self.recording
        msg.session_directory = str(self.session_dir) if self.session_dir else ""
        msg.status = status
        self.state_pub.publish(msg)

    def destroy_node(self):
        if self.recording:
            self._finish_recording("interrupted")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SessionManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
