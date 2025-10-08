"""
Curated layer builder from Chapter 4
Partition, optimize, and prepare for analytics
"""
import polars as pl
import os
import shutil

# Read from staging
staging_file = "data/staging/orders/snapshot_2024-01-15.parquet"
if not os.path.exists(staging_file):
    print("Error: Staging file not found. Run transform_orders.py first.")
    exit(1)

print(f"Reading {staging_file}...")
df = pl.read_parquet(staging_file)

# Add partition columns
curated_df = df.with_columns([
    pl.col("order_date").dt.year().alias("year"),
    pl.col("order_date").dt.month().alias("month"),
    pl.col("order_date").dt.day().alias("day")
]).sort("order_date")  # Sort for max compression

# Set output directory
output_path = "data/curated/orders_fact"

# Remove existing directory if it exists (for clean re-runs)
if os.path.exists(output_path):
    shutil.rmtree(output_path)

# Write partitioned
curated_df.write_parquet(
    output_path,
    partition_by=["year", "month"],
    use_pyarrow=True,
    compression="zstd",  # Better than snappy for analytics
    statistics=True      # Enable Parquet statistics for pruning
)

# Add trailing slash for display
output_path = output_path + "/"

print(f"✓ Curated {curated_df.height:,} rows to {output_path}")

# Show partition structure
for root, dirs, files in os.walk(output_path):
    level = root.replace(output_path, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    sub_indent = ' ' * 2 * (level + 1)
    for file in files:
        if file.endswith('.parquet'):
            size_mb = os.path.getsize(os.path.join(root, file)) / 1e6
            print(f'{sub_indent}{file} ({size_mb:.2f} MB)')
