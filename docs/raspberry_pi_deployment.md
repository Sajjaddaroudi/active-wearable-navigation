# Raspberry Pi Deployment

Target hardware is Raspberry Pi 4 with Ubuntu 22.04 ARM64 and ROS 2 Humble.

```bash
cd ~/REPOS/wearnav_ros2
./scripts/setup_pi.sh
```

The setup script checks Ubuntu version and architecture, installs ROS 2 Humble only if missing, installs `python3-websockets` for the generic app bridge, runs `rosdep`, and builds with `colcon`.

It does not change firmware, networking, Ubuntu release, Docker, or unrelated packages.

External app mode listens on `0.0.0.0:8765` by default:

```bash
ros2 launch wearnav_bringup app_system.launch.py
```

From a laptop on the same LAN, test the network path with:

```bash
python3 scripts/test_app_client.py --host <PI_IP> --label app_bridge_test
```
