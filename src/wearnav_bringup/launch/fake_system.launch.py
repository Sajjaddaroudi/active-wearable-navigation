from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

from pathlib import Path


def generate_launch_description():
    config = Path(get_package_share_directory("wearnav_bringup")) / "config" / "acquisition.yaml"
    return LaunchDescription(
        [
            Node(
                package="garmin_bridge",
                executable="fake_garmin_publisher",
                name="fake_garmin_publisher",
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

