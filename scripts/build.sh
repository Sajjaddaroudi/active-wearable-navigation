#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install

