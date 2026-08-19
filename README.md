# WearNav ROS 2 Acquisition

WearNav is a research ROS 2 stack for wearable indoor navigation and object-finding. This repository covers the data-acquisition path only, using simulated Garmin watch IMU data.

```text
fake Garmin data -> /wearnav/garmin/imu_raw -> converter -> /wearnav/garmin/imu
                                             -> session manager -> rosbag2
```

## Packages

- `wearnav_interfaces`: raw Garmin batch and session service definitions.
- `garmin_bridge`: fake Garmin publisher and IMU converter.
- `wearnav_recorder`: session services, metadata, and rosbag2 recording.
- `wearnav_bringup`: launch and acquisition configuration.

## Requirements

- Ubuntu 22.04
- ROS 2 Humble ros-base
- `rosbag2`, `ros-dev-tools`, `colcon`, `rosdep`

## Build

```bash
cd ~/REPOS/wearnav_ros2
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Launch

```bash
ros2 launch wearnav_bringup fake_system.launch.py
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

## Raspberry Pi Deployment

Clone this repository on Ubuntu 22.04 ARM64 and run:

```bash
cd ~/REPOS/wearnav_ros2
./scripts/setup_pi.sh
```

## Next Step

Replace `fake_garmin_publisher` with a network receiver fed by Garmin FR165 data through Android while keeping `/wearnav/garmin/imu_raw` unchanged.

