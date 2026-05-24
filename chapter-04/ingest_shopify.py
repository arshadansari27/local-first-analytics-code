"""
Raw ingestion script from Chapter 4
Simulates downloading data from Shopify API and saving to raw zone.

Generates a small synthetic export (a few hundred orders spread across a
handful of months) so the downstream partitioned writer actually produces
multiple partitions you can inspect.
"""
import polars as pl
from datetime import datetime, timedelta, timezone
import os
import gzip
import random

# Create raw directory
os.makedirs("data/raw/shopify_orders", exist_ok=True)

# Simulate downloading CSV from Shopify API
# In production, this would be: requests.get(shopify_api_url)
print("Downloading data from Shopify API...")

# Deterministic synthetic data so re-runs reproduce
random.seed(42)
N = 600
start = datetime(2024, 1, 1, 10, 30, 0)

# Spread orders across ~6 months so date partitioning has multiple buckets
created_at = [
    (start + timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d %H:%M:%S")
    for _ in range(N)
]

# For demo, generate sample data
df = pl.DataFrame({
    "id": list(range(1, N + 1)),
    "email": [f"customer{i}@example.com" for i in range(1, N + 1)],
    "created_at": created_at,
    "total_price": [round(random.uniform(20, 500), 2) for _ in range(N)],
    "financial_status": [
        random.choices(
            ["paid", "pending", "refunded"], weights=[80, 15, 5]
        )[0]
        for _ in range(N)
    ],
    "fulfillment_status": [
        random.choices(
            ["fulfilled", "pending", None], weights=[70, 25, 5]
        )[0]
        for _ in range(N)
    ],
})

# Save with timestamp (immutable, never overwrite)
raw_file = f"data/raw/shopify_orders/{datetime.now(timezone.utc).isoformat()}.csv.gz"

# Write CSV with gzip compression
csv_content = df.write_csv()
with gzip.open(raw_file, 'wt') as f:
    f.write(csv_content)

print(f"✓ Saved {len(df):,} rows to {raw_file}")
print(f"  File size: {os.path.getsize(raw_file) / 1e6:.2f} MB")
