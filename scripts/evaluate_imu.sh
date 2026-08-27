#!/usr/bin/env bash
set -eo pipefail

duration_s="${1:-15}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ros_distro="${ROS_DISTRO:-humble}"

if [[ "${duration_s}" =~ ^[0-9]+$ ]]; then
    duration_s="${duration_s}.0"
elif [[ ! "${duration_s}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "Duration must be a positive number of seconds." >&2
    exit 1
fi

if [[ ! -f "/opt/ros/${ros_distro}/setup.bash" ]]; then
    echo "ROS 2 ${ros_distro} was not found under /opt/ros." >&2
    exit 1
fi

if [[ ! -f "${repo_root}/install/setup.bash" ]]; then
    echo "WearNav is not built. Run: cd ${repo_root} && colcon build --symlink-install" >&2
    exit 1
fi

source "/opt/ros/${ros_distro}/setup.bash"
source "${repo_root}/install/setup.bash"
set -u

exec ros2 run garmin_bridge evaluate_imu --ros-args -p "duration_s:=${duration_s}"
