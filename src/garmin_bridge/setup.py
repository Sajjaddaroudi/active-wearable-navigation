from setuptools import find_packages, setup

package_name = "garmin_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="lisec",
    maintainer_email="lisec@todo.todo",
    description="Simulated Garmin IMU input and conversion nodes.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "app_command_bridge = garmin_bridge.app_command_bridge:main",
            "fake_garmin_publisher = garmin_bridge.fake_garmin_publisher:main",
            "garmin_imu_converter = garmin_bridge.garmin_imu_converter:main",
        ],
    },
)
