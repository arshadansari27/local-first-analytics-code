"""
Create Daily Summary (Materialized View)
Pre-aggregates trip data by date and zone for faster dashboard queries.
"""
import duckdb
import os

# Check if partitioned data exists
if not os.path.exists('data/staging/taxi/partitioned'):
    print("[ERROR] Partitioned data not found!")
    print("Please run 'python partition_by_month.py' first.")
    exit(1)

print("Creating daily summary (this may take 1-2 minutes)...")

con = duckdb.connect()

# First create the clean_trips view
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

# Create daily summary table (pre-aggregated)
con.execute("""
    COPY (
        SELECT
            pickup_date,
            pickup_zone,
            COUNT(*) AS trip_count,
            ROUND(SUM(clean_amount), 2) AS total_revenue,
            ROUND(AVG(clean_distance), 2) AS avg_distance,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY clean_amount), 2) AS median_fare
        FROM clean_trips
        GROUP BY 1, 2
    ) TO 'data/staging/taxi/daily_summary.parquet' (FORMAT PARQUET)
""")

con.close()

print("[OK] Created daily_summary.parquet")

# Show file size
if os.path.exists('data/staging/taxi/daily_summary.parquet'):
    size_mb = os.path.getsize('data/staging/taxi/daily_summary.parquet') / (1024 * 1024)
    print(f"\nFile size: {size_mb:.2f} MB")
    print("\nThis pre-aggregated summary enables millisecond queries for dashboards.")
