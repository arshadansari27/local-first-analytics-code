SCHEMA = """
Table: sensor_readings (Parquet, partitioned by date)
|-- timestamp (TIMESTAMP) - Reading time
|-- sensor_id (VARCHAR) - Unique sensor identifier
|-- device_type (VARCHAR) - pump|motor|compressor
|-- temperature (DOUBLE) - Celsius
|-- pressure (DOUBLE) - PSI
|-- vibration (DOUBLE) - mm/s
|-- status (VARCHAR) - normal|warning|critical
+-- facility (VARCHAR) - Building location

Partitions: data/sensors/year=YYYY/month=MM/day=DD/*.parquet
Row count: variable (depends on generation)
Date range: configurable (defaults to 2024-12 only)

Example queries:
- "errors last week" -> WHERE status='critical' AND timestamp > current_date - 7
- "facility B03" -> WHERE facility='B03'
"""
