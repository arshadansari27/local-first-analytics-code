"""
Download NYC Taxi Trip Data (2023)
Downloads 12 monthly Parquet files from NYC TLC and converts to optimized format.
"""
import duckdb
from pathlib import Path

# DuckDB can download and convert to Parquet in one shot
con = duckdb.connect()

# Create output directory
Path("data/raw/taxi").mkdir(parents=True, exist_ok=True)

# Download all 2023 monthly files and convert to Parquet
# This grabs ~50M rows total
for month in range(1, 13):
    url = (
        f"https://d37ci6vzurychx.cloudfront.net/trip-data/"
        f"yellow_tripdata_2023-{month:02d}.parquet"
    )
    output = f"data/raw/taxi/yellow_tripdata_2023-{month:02d}.parquet"

    con.execute(f"""
        COPY (
            SELECT * FROM read_parquet('{url}')
        ) TO '{output}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    print(f"[OK] Downloaded month {month}")

con.close()

print("\n[COMPLETE] All 12 months downloaded")
print("Data saved to: data/raw/taxi/")
