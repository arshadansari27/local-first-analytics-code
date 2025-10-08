"""
Build Portable DuckDB Warehouse
Creates a .duckdb file with views, macros, and metadata pointing to Parquet files.
"""
import duckdb
import os
from pathlib import Path

# Check prerequisites
if not os.path.exists('data/staging/taxi/partitioned'):
    print("[ERROR] Partitioned data not found!")
    print("Please run 'python partition_by_month.py' first.")
    exit(1)

print("Building portable warehouse...")

# Create a persistent .duckdb file
con = duckdb.connect('data/taxi_warehouse.duckdb')

# Attach Parquet files as external tables
con.execute("""
    CREATE OR REPLACE VIEW trips AS
    SELECT * FROM read_parquet('data/staging/taxi/partitioned/**/*.parquet')
""")
print("[OK] Created 'trips' view")

# Create daily_summary view only if the file exists
if os.path.exists('data/staging/taxi/daily_summary.parquet'):
    con.execute("""
        CREATE OR REPLACE VIEW daily_summary AS
        SELECT * FROM read_parquet('data/staging/taxi/daily_summary.parquet')
    """)
    print("[OK] Created 'daily_summary' view")
else:
    print("[SKIP] daily_summary.parquet not found (optional)")
    print("       Run the notebook to create materialized summaries")

# Create clean_trips view with data quality rules
con.execute("""
    CREATE OR REPLACE VIEW clean_trips AS
    SELECT
        tpep_pickup_datetime AS pickup_time,
        tpep_dropoff_datetime AS dropoff_time,
        DATE_TRUNC('day', tpep_pickup_datetime) AS pickup_date,
        passenger_count,
        trip_distance,
        PULocationID AS pickup_zone,
        DOLocationID AS dropoff_zone,
        RatecodeID AS rate_code,
        payment_type,
        fare_amount,
        tip_amount,
        total_amount,
        -- Clean nulls and outliers
        CASE
            WHEN trip_distance <= 0 THEN NULL
            WHEN trip_distance > 100 THEN NULL
            ELSE trip_distance
        END AS clean_distance,
        CASE
            WHEN total_amount < 0 THEN NULL
            WHEN total_amount > 500 THEN NULL
            ELSE total_amount
        END AS clean_amount
    FROM read_parquet('data/staging/taxi/partitioned/**/*.parquet')
    WHERE passenger_count > 0
        AND fare_amount >= 0
""")
print("[OK] Created 'clean_trips' view")

# Add macros for reusable calculations
con.execute("""
    CREATE OR REPLACE MACRO trip_efficiency(distance, duration_minutes) AS (
        CASE
            WHEN duration_minutes = 0 THEN NULL
            ELSE (distance / duration_minutes) * 60
        END
    )
""")
print("[OK] Created 'trip_efficiency' macro")

# Show warehouse info
result = con.execute("SELECT COUNT(*) FROM trips").fetchone()
print(f"\n[COMPLETE] Warehouse built: data/taxi_warehouse.duckdb")
print(f"Total trips: {result[0]:,}")

con.close()

# Show file size
import os
if os.path.exists('data/taxi_warehouse.duckdb'):
    size_kb = os.path.getsize('data/taxi_warehouse.duckdb') / 1024
    print(f"Warehouse file size: {size_kb:.1f} KB")
    print("\nNote: The .duckdb file only stores metadata and views.")
    print("All data remains in Parquet files.")
