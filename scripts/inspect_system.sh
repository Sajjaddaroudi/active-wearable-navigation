#!/usr/bin/env bash
set -euo pipefail

source /opt/ros/humble/setup.bash
source "$(dirname "$0")/../install/setup.bash"
ros2 node list
ros2 topic list
ros2 service list

