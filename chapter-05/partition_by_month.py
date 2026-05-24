"""
Partition Taxi Data by Month
Repartitions raw taxi data into monthly partitions for faster queries.
"""
import duckdb
from pathlib import Path
import glob

# Check if taxi data exists
taxi_files = glob.glob("data/raw/taxi/yellow_tripdata_*.parquet")
if not taxi_files:
    print("[ERROR] No taxi data found!")
    print("Please run 'python download_taxi_data.py' first to download the data.")
    exit(1)

print(f"Found {len(taxi_files)} taxi data files")

con = duckdb.connect()

# Create partitioned output directory
Path("data/staging/taxi/partitioned").mkdir(parents=True, exist_ok=True)

print("Partitioning taxi data by month...")
print("This may take a few minutes for 50M rows...")

# Repartition by month. Two practical notes:
# (1) TLC source files contain a small number of out-of-range pickup dates
#     (the January 2023 file has a handful of 2008/2022/2024 rows). Filter
#     to the expected calendar year so partitions stay tidy.
# (2) Cast DATE_TRUNC's result to DATE — DuckDB writes TIMESTAMP partition
#     keys as URL-encoded directory names (e.g. ``2023-01-01%2000%3A00%3A00``),
#     which is ugly and breaks glob patterns. DATE gives ``2023-01-01``.
con.execute("""
    COPY (
        SELECT
            *,
            CAST(DATE_TRUNC('month', tpep_pickup_datetime) AS DATE) AS pickup_month
        FROM read_parquet('data/raw/taxi/yellow_tripdata_*.parquet')
        WHERE tpep_pickup_datetime >= TIMESTAMP '2023-01-01'
          AND tpep_pickup_datetime <  TIMESTAMP '2024-01-01'
    )
    TO 'data/staging/taxi/partitioned'
    (FORMAT PARQUET, PARTITION_BY (pickup_month), OVERWRITE_OR_IGNORE)
""")

print("\n[OK] Partitioning complete")

# Show partition structure
import os
partition_dir = "data/staging/taxi/partitioned"
if os.path.exists(partition_dir):
    partitions = sorted([d for d in os.listdir(partition_dir) if d.startswith("pickup_month=")])
    print(f"\nCreated {len(partitions)} partitions:")
    for p in partitions[:3]:
        print(f"  - {p}/")
    if len(partitions) > 3:
        print(f"  ... and {len(partitions) - 3} more")

con.close()
