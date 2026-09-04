cmake_minimum_required(VERSION 3.8)
project(wearnav_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/GarminImuBatch.msg"
  "msg/BleRssiReading.msg"
  "msg/SessionState.msg"
  "srv/StartSession.srv"
  "srv/StopSession.srv"
  DEPENDENCIES std_msgs
)

ament_package()

