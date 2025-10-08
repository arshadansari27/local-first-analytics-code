"""
Raw ingestion script from Chapter 4
Simulates downloading data from Shopify API and saving to raw zone
"""
import polars as pl
from datetime import datetime, timezone
import os
import gzip

# Create raw directory
os.makedirs("data/raw/shopify_orders", exist_ok=True)

# Simulate downloading CSV from Shopify API
# In production, this would be: requests.get(shopify_api_url)
print("Downloading data from Shopify API...")

# For demo, generate sample data
df = pl.DataFrame({
    "id": range(1, 10001),
    "email": [f"customer{i}@example.com" for i in range(1, 10001)],
    "created_at": ["2024-01-15 10:30:00"] * 10000,
    "total_price": [round(i * 0.5 + 20, 2) for i in range(1, 10001)],
    "financial_status": ["paid"] * 8000 + ["pending"] * 1500 + ["refunded"] * 500,
    "fulfillment_status": ["fulfilled"] * 7000 + ["pending"] * 2500 + [None] * 500
})

# Save with timestamp (immutable, never overwrite)
raw_file = f"data/raw/shopify_orders/{datetime.now(timezone.utc).isoformat()}.csv.gz"

# Write CSV with gzip compression
csv_content = df.write_csv()
with gzip.open(raw_file, 'wt') as f:
    f.write(csv_content)

print(f"✓ Saved {len(df):,} rows to {raw_file}")
print(f"  File size: {os.path.getsize(raw_file) / 1e6:.2f} MB")
