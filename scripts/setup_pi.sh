#!/usr/bin/env bash
set -euo pipefail

if ! lsb_release -rs | grep -q '^22\.04$'; then
  echo "Ubuntu 22.04 is required"
  exit 1
fi

arch="$(uname -m)"
case "$arch" in
  aarch64|arm64) ;;
  *) echo "Warning: expected Raspberry Pi ARM64, found $arch" ;;
esac

if [ ! -f /opt/ros/humble/setup.bash ]; then
  sudo apt update
  sudo apt install -y software-properties-common curl gnupg lsb-release
  sudo add-apt-repository universe -y
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
  sudo apt update
  sudo apt install -y ros-humble-ros-base ros-dev-tools python3-colcon-common-extensions python3-rosdep python3-websockets
fi

sudo apt install -y python3-websockets

source /opt/ros/humble/setup.bash
sudo rosdep init 2>/dev/null || true
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
echo "WearNav ROS 2 setup complete"
