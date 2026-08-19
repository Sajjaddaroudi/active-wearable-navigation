#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch wearnav_bringup fake_system.launch.py

