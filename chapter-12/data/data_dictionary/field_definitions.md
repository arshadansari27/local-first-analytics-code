# Field Definitions

- `timestamp`: Reading time (TIMESTAMP, UTC)
- `sensor_id`: Unique sensor identifier (VARCHAR)
- `device_type`: One of `pump`, `motor`, `compressor`
- `temperature`: Sensor temperature in Celsius (DOUBLE)
- `pressure`: Sensor pressure in PSI (DOUBLE)
- `vibration`: Mechanical vibration in mm/s (DOUBLE)
- `status`: One of `normal`, `warning`, `critical`
- `facility`: Building/facility code (VARCHAR)
