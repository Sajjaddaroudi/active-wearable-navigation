from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = Path(get_package_share_directory("wearnav_bringup")) / "config" / "acquisition.yaml"
    return LaunchDescription(
        [
            Node(
                package="garmin_bridge",
                executable="app_command_bridge",
                name="app_command_bridge",
                parameters=[str(config)],
            ),
            Node(
                package="garmin_bridge",
                executable="garmin_imu_converter",
                name="garmin_imu_converter",
                parameters=[str(config)],
            ),
            Node(
                package="wearnav_recorder",
                executable="session_manager",
                name="session_manager",
                parameters=[str(config)],
            ),
        ]
    )

