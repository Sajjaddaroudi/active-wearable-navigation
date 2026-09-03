std_msgs/Header header

string session_id
uint32 sequence

uint64[] watch_timestamp_ms

float32[] accel_x_mg
float32[] accel_y_mg
float32[] accel_z_mg

float32[] gyro_x_deg_s
float32[] gyro_y_deg_s
float32[] gyro_z_deg_s
bool gyro_available

float32[] mag_x_mgauss
float32[] mag_y_mgauss
float32[] mag_z_mgauss
bool mag_available

float32 altitude_m
bool altitude_available

uint64 phone_receive_time_ns
uint64 pi_receive_time_ns

