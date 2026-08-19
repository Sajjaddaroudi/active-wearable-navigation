# Raspberry Pi Deployment

Target hardware is Raspberry Pi 4 with Ubuntu 22.04 ARM64 and ROS 2 Humble.

```bash
cd ~/REPOS/wearnav_ros2
./scripts/setup_pi.sh
```

The setup script checks Ubuntu version and architecture, installs ROS 2 Humble only if missing, runs `rosdep`, and builds with `colcon`.

It does not change firmware, networking, Ubuntu release, Docker, or unrelated packages.

