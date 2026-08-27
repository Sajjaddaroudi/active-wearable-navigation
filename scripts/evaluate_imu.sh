#!/usr/bin/env bash
set -eo pipefail

trial_path="${1:-}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ros_distro="${ROS_DISTRO:-humble}"

if [[ -z "${trial_path}" ]]; then
    echo "Usage: $0 ~/wearnav_data/<session_id> [evaluator options]" >&2
    echo "Available sessions:" >&2
    find "${HOME}/wearnav_data" -mindepth 1 -maxdepth 1 -type d \
        -printf '  %p\n' 2>/dev/null | sort >&2 || true
    exit 2
fi
shift

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

exec ros2 run garmin_bridge evaluate_imu "${trial_path}" "$@"
