"""
Download NYC Taxi Trip Data (2023)
Downloads monthly Parquet files from NYC TLC and converts to optimized format.

NOTE: To keep this chapter runnable on a laptop with limited bandwidth, the
demo defaults to a SINGLE month (January 2023, ~3M rows, ~48MB). Set
MONTHS = range(1, 13) to download the full year (~38M rows, ~600MB) and
reproduce the benchmarks discussed in the chapter text.
"""
import duckdb
from pathlib import Path

# DuckDB can download and convert to Parquet in one shot
con = duckdb.connect()

# Create output directory
Path("data/raw/taxi").mkdir(parents=True, exist_ok=True)

# Demo default: just January. Expand to range(1, 13) for the full 2023 year.
MONTHS = [1]

for month in MONTHS:
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

print(f"\n[COMPLETE] Downloaded {len(MONTHS)} month(s)")
print("Data saved to: data/raw/taxi/")
