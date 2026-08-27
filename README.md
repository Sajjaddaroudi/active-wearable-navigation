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

## Validate Physical IMU Data

With `app_system.launch.py` running and the phone sending watch data, run the
evaluation for 15 seconds. Keep the watch still for a moment, then rotate it
around several axes so the gyroscope can be verified:

```bash
./scripts/evaluate_imu.sh 15
```

The command prints each received batch and finishes with individual checks for
the publisher identity, array integrity, timestamp/sample rate, transport gaps,
gravity-scale acceleration, and rotation detected by the gyroscope. A successful
physical six-axis stream ends with:

```text
RESULT: PASS - physical six-axis IMU data looks valid
```

The equivalent ROS command is:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run garmin_bridge evaluate_imu --ros-args -p duration_s:=15.0
```

Add `-p show_samples:=true` to the ROS command to print every accelerometer and
gyroscope sample rather than one summary line per batch.

## Raspberry Pi Deployment

Clone this repository on Ubuntu 22.04 ARM64 and run:

```bash
cd ~/REPOS/wearnav_ros2
./scripts/setup_pi.sh
```

## Next Step

Connect a real external application to `app_command_bridge` while keeping `/wearnav/garmin/imu_raw` unchanged.
