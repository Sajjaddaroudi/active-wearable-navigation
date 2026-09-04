std_msgs/Header header

string session_id
uint32 sequence

# The scanning phone forwards these directly (no watch/device batching
# involved - unlike GarminImuBatch, this is one event, not a per-second
# batch of samples).
string beacon_id
int32 rssi_dbm

uint64 phone_receive_time_ns
uint64 pi_receive_time_ns
