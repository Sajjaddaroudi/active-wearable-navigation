from setuptools import find_packages, setup

package_name = "wearnav_recorder"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    maintainer="lisec",
    maintainer_email="lisec@todo.todo",
    description="Session control and rosbag recording for WearNav.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "session_manager = wearnav_recorder.session_manager:main",
        ],
    },
)

