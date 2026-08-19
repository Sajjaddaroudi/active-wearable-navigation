# Architecture

The current stack validates acquisition, conversion, session control, and rosbag output without Garmin, Android, BLE, DRL, or Raspberry Pi hardware code.

```text
fake_garmin_publisher
  publishes /wearnav/garmin/imu_raw

garmin_imu_converter
  subscribes /wearnav/garmin/imu_raw
  publishes /wearnav/garmin/imu

session_manager
  exposes /wearnav/session/start and /wearnav/session/stop
  publishes /wearnav/session/state
  records selected topics to rosbag2
```

The raw Garmin batch message keeps watch timestamps and phone/Pi receive time fields so future clock work can be added without changing the recorder or downstream consumers.

Future source path:

```text
Garmin FR165 -> Android -> Raspberry Pi receiver -> /wearnav/garmin/imu_raw
```

Future topics may include phone IMU, BLE RSSI, user state, target belief, policy action, and haptic command topics. They are intentionally not implemented here.

