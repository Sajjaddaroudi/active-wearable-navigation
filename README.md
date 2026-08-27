# WearNav ROS 2 Acquisition

WearNav is a research ROS 2 stack for wearable indoor navigation and object-finding. This repository covers the data-acquisition path only, using simulated Garmin watch IMU data or Garmin-shaped batches from a generic external application.

```text
fake Garmin data -> /wearnav/garmin/imu_raw -> converter -> /wearnav/garmin/imu
                                             -> session manager -> rosbag2
```

## Packages

- `wearnav_interfaces`: raw Garmin batch and session service definitions.
- `garmin_bridge`: fake Garmin publisher, generic app bridge, and IMU converter.
- `wearnav_recorder`: session services, metadata, and rosbag2 recording.
- `wearnav_bringup`: launch and acquisition configuration.

## Requirements

- Ubuntu 22.04
- ROS 2 Humble ros-base
- `rosbag2`, `ros-dev-tools`, `colcon`, `rosdep`
- `python3-websockets`

## Build

```bash
cd ~/REPOS/wearnav_ros2
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Launch

Fake development source:

```bash
ros2 launch wearnav_bringup fake_system.launch.py
```

Generic external application source:

```bash
ros2 launch wearnav_bringup app_system.launch.py
```

## Generic External App Bridge

`app_command_bridge` listens for WebSocket JSON messages on `0.0.0.0:8765` by default. It accepts protocol version `1` messages of type `hello`, `ping`, `start_session`, `stop_session`, and `imu_batch`.

The bridge is platform independent. Android, iPhone, Windows, Linux, web, or embedded clients can all use the same JSON protocol later. The bridge publishes Garmin-shaped IMU batches to `/wearnav/garmin/imu_raw` and delegates recording control to the existing `/wearnav/session/start` and `/wearnav/session/stop` services.

Local test client:

```bash
python3 scripts/test_app_client.py --host 127.0.0.1 --label app_bridge_test
```

## Recording

Start:

```bash
ros2 service call /wearnav/session/start wearnav_interfaces/srv/StartSession "{label: 'walk_forward_test'}"
```

Stop:

```bash
ros2 service call /wearnav/session/stop wearnav_interfaces/srv/StopSession "{}"
```

Sessions are written under `~/wearnav_data/<session_id>/` with `metadata.yaml` and `bag/`.

Inspect and replay:

```bash
ros2 bag info ~/wearnav_data/<session_id>/bag
ros2 bag play ~/wearnav_data/<session_id>/bag
```

## Evaluate a Recorded IMU Trial Offline

Evaluate one saved session directly from its rosbag. The phone, watch, bridge,
and ROS launch system do not need to be running:

```bash
./scripts/evaluate_imu.sh ~/wearnav_data/<session_id>
```

The path can be the session directory, its `bag/` directory, its bag
`metadata.yaml`, or its `.db3` file. The command prints each recorded batch and
checks array integrity, timestamp/sample rate, recorded batch cadence, transport
gaps, gravity-scale acceleration, and gyroscope motion. A valid recorded
six-axis trial ends with:

```text
RESULT: PASS - recorded six-axis IMU data looks valid
```

This verifies the recorded values and timing. A rosbag does not retain enough
publisher identity to prove by itself that the source was a physical watch, so
the report marks source provenance as a warning rather than claiming it.

The equivalent ROS command is:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run garmin_bridge evaluate_imu ~/wearnav_data/<session_id>
```

Add `--show-samples` to print every accelerometer and gyroscope sample rather
than one summary line per batch.

## Raspberry Pi Deployment

Clone this repository on Ubuntu 22.04 ARM64 and run:

```bash
cd ~/REPOS/wearnav_ros2
./scripts/setup_pi.sh
```

## Next Step

Connect a real external application to `app_command_bridge` while keeping `/wearnav/garmin/imu_raw` unchanged.
