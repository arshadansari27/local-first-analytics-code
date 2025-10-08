"""
Staging transformation script from Chapter 4
Clean, validate, and type raw data
"""
import polars as pl
import os
from glob import glob

# Find latest raw file
raw_files = sorted(glob("data/raw/shopify_orders/*.csv.gz"))
if not raw_files:
    print("Error: No raw files found. Run ingest_shopify.py first.")
    exit(1)

latest_raw = raw_files[-1]
print(f"Processing {latest_raw}...")

# Read raw data
df = pl.read_csv(latest_raw)

# Clean and type
staging_df = df.select([
    pl.col("id").cast(pl.Int64).alias("order_id"),
    pl.col("email").str.to_lowercase().alias("customer_email"),
    pl.col("created_at").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S").alias("order_date"),
    pl.col("total_price").cast(pl.Float64).alias("revenue"),
    pl.col("financial_status").alias("payment_status"),
    pl.col("fulfillment_status").alias("fulfillment_status")
]).filter(
    pl.col("revenue") > 0  # Drop test orders
)

# Data quality checks
null_counts = staging_df.null_count()
total_nulls = null_counts.sum_horizontal()[0]
if total_nulls > 0:
    print(f"Warning: {total_nulls} null values detected")
    print(f"Null count per column:\n{null_counts}")

assert staging_df.height > 0, "Empty dataframe after filtering!"

# Save to staging
os.makedirs("data/staging/orders", exist_ok=True)
staging_file = "data/staging/orders/snapshot_2024-01-15.parquet"
staging_df.write_parquet(staging_file)

print(f"✓ Staged {staging_df.height:,} rows to {staging_file}")
print(f"  File size: {os.path.getsize(staging_file) / 1e6:.2f} MB")
