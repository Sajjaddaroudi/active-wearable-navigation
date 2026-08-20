# Architecture

The current stack validates acquisition, conversion, session control, and rosbag output without real Garmin, BLE, localization, DRL, or haptic code.

## Fake Development Mode

```text
fake_garmin_publisher
        |
        v
/wearnav/garmin/imu_raw
        |
        v
garmin_imu_converter
        |
        v
/wearnav/garmin/imu
```

## External Application Mode

```text
Android / iPhone / Windows / Linux
               |
               | WebSocket JSON
               v
       app_command_bridge
               |
       +-------+-------+
       |               |
       v               v
Garmin IMU raw    session services
       |               |
       v               v
/wearnav/        session_manager
garmin/imu_raw         |
       |               v
       v             rosbag2
garmin_imu_converter
       |
       v
/wearnav/garmin/imu
```

The ROS side is intentionally independent of the application platform. The external client only needs to speak the versioned WebSocket JSON protocol.

## Core ROS Responsibilities

```text
app_command_bridge
  listens for WebSocket JSON
  publishes /wearnav/garmin/imu_raw
  calls /wearnav/session/start and /wearnav/session/stop

garmin_imu_converter
  subscribes /wearnav/garmin/imu_raw
  publishes /wearnav/garmin/imu

session_manager
  owns recording state
  exposes /wearnav/session/start and /wearnav/session/stop
  publishes /wearnav/session/state
  records selected topics to rosbag2
```

The raw Garmin batch message keeps watch timestamps and phone/Pi receive time fields so future clock work can be added without changing the recorder or downstream consumers.

Future topics may include phone IMU, BLE RSSI, user state, target belief, policy action, and haptic command topics. They are intentionally not implemented here.
