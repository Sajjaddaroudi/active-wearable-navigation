import asyncio
import json
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data

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
from garmin_bridge.websockets_compat import patch_websockets_asyncio
from wearnav_interfaces.msg import GarminImuBatch, SessionState
from wearnav_interfaces.srv import StartSession, StopSession


patch_websockets_asyncio()
import websockets


class AppCommandBridge(Node):
    def __init__(self):
        super().__init__("app_command_bridge")
        self.declare_parameter("host", "0.0.0.0")
        self.declare_parameter("port", 8765)
        self.declare_parameter("frame_id", "garmin_watch")

        self.host = str(self.get_parameter("host").value)
        self.port = int(self.get_parameter("port").value)
        self.frame_id = str(self.get_parameter("frame_id").value)

        self.imu_pub = self.create_publisher(
            GarminImuBatch, "/wearnav/garmin/imu_raw", qos_profile_sensor_data
        )
        self.start_client = self.create_client(StartSession, "/wearnav/session/start")
        self.stop_client = self.create_client(StopSession, "/wearnav/session/stop")

        qos = QoSProfile(depth=1)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.state_sub = self.create_subscription(
            SessionState, "/wearnav/session/state", self._state_callback, qos
        )

        self._state_lock = threading.Lock()
        self._recording = False
        self._session_id = UNASSIGNED_SESSION

        self._loop = None
        self._stop_event = None
        self._ready = threading.Event()
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()

    def _state_callback(self, msg):
        with self._state_lock:
            self._recording = bool(msg.recording)
            self._session_id = msg.session_id if msg.recording and msg.session_id else UNASSIGNED_SESSION

    def _current_state(self):
        with self._state_lock:
            return self._recording, self._session_id

    def _run_server(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()
        self._ready.set()
        self._loop.run_until_complete(self._serve())
        self._loop.close()

    async def _serve(self):
        async with websockets.serve(self._handle_client, self.host, self.port):
            self.get_logger().info(f"app command bridge listening on {self.host}:{self.port}")
            await self._stop_event.wait()

    async def _handle_client(self, websocket, path=None):
        peer = getattr(websocket, "remote_address", None)
        self.get_logger().info(f"client connected: {peer}")
        try:
            async for raw in websocket:
                response = await self._handle_message(raw)
                await websocket.send(json.dumps(response))
        finally:
            self.get_logger().info(f"client disconnected: {peer}")

    async def _handle_message(self, raw):
        data, error = parse_json(raw)
        if error:
            return error

        error = validate_envelope(data)
        if error:
            return error

        msg_type = data["type"]
        if msg_type == "hello":
            recording, session_id = self._current_state()
            return hello_response(data, recording, session_id)
        if msg_type == "ping":
            return ping_response()
        if msg_type == "start_session":
            return await self._start_session(str(data.get("label", "")))
        if msg_type == "stop_session":
            return await self._stop_session()
        if msg_type == "imu_batch":
            return self._publish_imu_batch(data)
        return error_response("Unsupported message type")

    async def _start_session(self, label):
        if not await self._wait_for_service(self.start_client):
            return {
                "type": "session_started",
                "version": 1,
                "success": False,
                "message": "start service unavailable",
            }

        request = StartSession.Request()
        request.label = label
        try:
            response = await self._await_ros_future(self.start_client.call_async(request))
        except TimeoutError:
            return {
                "type": "session_started",
                "version": 1,
                "success": False,
                "message": "start service timeout",
            }

        return {
            "type": "session_started",
            "version": 1,
            "success": bool(response.success),
            "session_id": response.session_id,
            "session_directory": response.session_directory,
            "message": response.message,
        }

    async def _stop_session(self):
        if not await self._wait_for_service(self.stop_client):
            return {
                "type": "session_stopped",
                "version": 1,
                "success": False,
                "message": "stop service unavailable",
            }

        try:
            response = await self._await_ros_future(
                self.stop_client.call_async(StopSession.Request())
            )
        except TimeoutError:
            return {
                "type": "session_stopped",
                "version": 1,
                "success": False,
                "message": "stop service timeout",
            }

        return {
            "type": "session_stopped",
            "version": 1,
            "success": bool(response.success),
            "session_id": response.session_id,
            "session_directory": response.session_directory,
            "message": response.message,
        }

    async def _wait_for_service(self, client, timeout_s=5.0):
        deadline = self.get_clock().now().nanoseconds + int(timeout_s * 1_000_000_000)
        while rclpy.ok() and self.get_clock().now().nanoseconds < deadline:
            if client.service_is_ready():
                return True
            await asyncio.sleep(0.05)
        return False

    async def _await_ros_future(self, future, timeout_s=15.0):
        deadline = self.get_clock().now().nanoseconds + int(timeout_s * 1_000_000_000)
        while rclpy.ok() and self.get_clock().now().nanoseconds < deadline:
            if future.done():
                return future.result()
            await asyncio.sleep(0.02)
        raise TimeoutError

    def _publish_imu_batch(self, data):
        if not validate_imu_batch(data):
            return error_response("Invalid IMU batch")

        try:
            now = self.get_clock().now()
            _, session_id = self._current_state()
            batch = batch_from_json(data, session_id, now.to_msg(), self.frame_id, now.nanoseconds)
        except (TypeError, ValueError, OverflowError):
            return error_response("Invalid IMU batch")

        self.imu_pub.publish(batch)
        return imu_ack(batch.sequence)

    def destroy_node(self):
        if self._ready.wait(timeout=1.0) and self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
            self._server_thread.join(timeout=3.0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = AppCommandBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
