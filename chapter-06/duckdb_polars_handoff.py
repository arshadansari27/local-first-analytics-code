#!/usr/bin/env python3
"""
DuckDB <-> Polars Zero-Copy Handoff

Demonstrates seamless data transfer between DuckDB and Polars using Apache Arrow.
No copying means instant transfer even for gigabyte-scale datasets.
"""

import polars as pl
import duckdb
from datetime import datetime
from pathlib import Path


def example_1_sql_to_transforms():
    """
    Pattern 1: DuckDB for complex SQL, Polars for transforms

    Use case: DuckDB handles window functions, Polars handles row transforms
    """
    print("=== Pattern 1: DuckDB SQL -> Polars Transforms ===\n")

    # Create sample events data
    events = pl.DataFrame({
        "user_id": [1, 1, 1, 2, 2, 3, 3, 3, 3],
        "session_id": ["S1", "S1", "S2", "S3", "S3", "S4", "S4", "S4", "S5"],
        "event_time": [
            datetime(2024, 10, 1, 10, 0, 0),
            datetime(2024, 10, 1, 10, 5, 0),
            datetime(2024, 10, 1, 11, 0, 0),
            datetime(2024, 10, 1, 9, 30, 0),
            datetime(2024, 10, 1, 9, 45, 0),
            datetime(2024, 10, 1, 14, 0, 0),
            datetime(2024, 10, 1, 14, 20, 0),
            datetime(2024, 10, 1, 14, 25, 0),
            datetime(2024, 10, 1, 15, 30, 0),
        ],
        "event_date": [datetime(2024, 10, 1).date()] * 9,
    })

    # DuckDB: Complex window functions (LAG to get previous event time).
    # `to_arrow_table()` returns a zero-copy `pyarrow.Table`. (Older code
    # used `fetch_arrow_table()`; that name is deprecated.)
    con = duckdb.connect()
    arrow_table = con.execute("""
        SELECT
            user_id,
            session_id,
            event_time,
            LAG(event_time) OVER (
                PARTITION BY user_id
                ORDER BY event_time
            ) as prev_event_time
        FROM events
        WHERE event_date = '2024-10-01'
    """).to_arrow_table()

    print("Step 1: DuckDB executed window function")
    print(f"  Returned {len(arrow_table)} rows via Arrow\n")

    # Polars: Fast column operations (calculate session gaps)
    df = pl.from_arrow(arrow_table)
    df = df.with_columns(
        (pl.col("event_time") - pl.col("prev_event_time"))
        .dt.total_seconds()
        .alias("session_gap_seconds")
    ).filter(pl.col("session_gap_seconds") > 1800)

    print("Step 2: Polars calculated session gaps > 30 minutes")
    print(df)
    print()

    # Back to DuckDB for final aggregation
    con.execute("""
        CREATE TABLE session_stats AS
        SELECT * FROM df
    """)

    stats = con.execute("""
        SELECT
            user_id,
            COUNT(*) as large_gap_count,
            AVG(session_gap_seconds) as avg_gap_seconds
        FROM session_stats
        GROUP BY user_id
    """).df()

    print("Step 3: Back to DuckDB for aggregation")
    print(stats)
    print()

    con.close()


def example_2_etl_to_serving():
    """
    Pattern 2: Polars for ETL, DuckDB for serving

    Use case: Polars cleans raw data, DuckDB queries the result
    """
    print("=== Pattern 2: Polars ETL -> DuckDB Serving ===\n")

    # Create output directories
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/curated").mkdir(parents=True, exist_ok=True)

    # Create sample customer data with issues
    customer_data = pl.DataFrame({
        "email": ["Alice@Example.com", "bob@test.COM", "Charlie@DEMO.org", "dave@site.NET"],
        "revenue": [1500.0, None, 2300.0, 450.0],
        "country": ["US", None, "CA", "UK"],
    })

    customer_data.write_csv("data/raw/customers.csv")

    # Polars: Transform and clean
    print("Step 1: Polars cleaning raw CSV data")
    cleaned = (
        pl.scan_csv("data/raw/customers.csv")
        .with_columns([
            pl.col("email").str.to_lowercase().alias("email_clean"),
            pl.col("revenue").fill_null(0),
            pl.when(pl.col("country").is_null())
              .then(pl.lit("UNKNOWN"))
              .otherwise(pl.col("country"))
              .alias("country_clean")
        ])
        .collect()
    )

    print("  Cleaned data:")
    print(cleaned)
    print()

    # Write to Parquet
    cleaned.write_parquet("data/curated/customers.parquet")
    print("Step 2: Wrote cleaned data to Parquet\n")

    # Query with DuckDB
    print("Step 3: DuckDB querying cleaned Parquet")
    result = duckdb.sql("""
        SELECT
            country_clean,
            COUNT(*) as customer_count,
            SUM(revenue) as total_revenue,
            ROUND(AVG(revenue), 2) as avg_revenue
        FROM 'data/curated/customers.parquet'
        GROUP BY country_clean
        ORDER BY total_revenue DESC
    """)

    print(result.df())
    print()


def example_3_streaming_pattern():
    """
    Streaming pattern: Process large datasets in chunks

    Use case: 100M+ row reconciliation without OOM errors
    """
    print("=== Pattern 3: Streaming for Large Datasets ===\n")

    print("For datasets > 100M rows, process in chunks:\n")

    print("# Bad: Loads everything into memory (OOM risk)")
    print("all_data = pl.scan_parquet('data/*.parquet').collect()  # DON'T DO THIS\n")

    print("# Good: Process one chunk at a time")
    print("for month_file in ['2024-01.parquet', '2024-02.parquet', ...]:")
    print("    chunk = (")
    print("        pl.scan_parquet(f'bank/{month_file}')")
    print("        .join(pl.scan_parquet(f'ledger/{month_file}'), ...)")
    print("        .filter(...)")
    print("        .collect()  # Only one chunk in memory")
    print("    )")
    print("    chunk.write_parquet(f'output/{month_file}')\n")

    print("# Then aggregate across all chunks with DuckDB")
    print("duckdb.sql('''")
    print("    SELECT status, COUNT(*), SUM(amount)")
    print("    FROM 'output/*.parquet'")
    print("    GROUP BY status")
    print("''').show()")
    print()


def main():
    """Run all DuckDB <-> Polars handoff examples."""

    print("\n" + "="*60)
    print("DuckDB <-> Polars Zero-Copy Integration")
    print("="*60 + "\n")

    # Pattern 1: SQL to transforms
    example_1_sql_to_transforms()

    print("\n" + "-"*60 + "\n")

    # Pattern 2: ETL to serving
    example_2_etl_to_serving()

    print("\n" + "-"*60 + "\n")

    # Pattern 3: Streaming
    example_3_streaming_pattern()

    print("="*60)
    print("\nKey Takeaway:")
    print("  - DuckDB: Window functions, complex joins, ad-hoc queries")
    print("  - Polars: Row transforms, deduplication, data cleaning")
    print("  - Use them together via Apache Arrow (zero-copy)")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
