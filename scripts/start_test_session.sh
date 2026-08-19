#!/usr/bin/env bash
set -euo pipefail

source /opt/ros/humble/setup.bash
source "$(dirname "$0")/../install/setup.bash"
ros2 service call /wearnav/session/start wearnav_interfaces/srv/StartSession "{label: 'walk_forward_test'}"

