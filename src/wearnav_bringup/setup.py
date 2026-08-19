from glob import glob

from setuptools import find_packages, setup

package_name = "wearnav_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="lisec",
    maintainer_email="lisec@todo.todo",
    description="Launch and configuration for WearNav acquisition.",
    license="Apache-2.0",
)

