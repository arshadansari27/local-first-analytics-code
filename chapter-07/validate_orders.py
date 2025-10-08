"""
Chapter 7: Complete Quality Pipeline

Full end-to-end quality validation pipeline combining all three tiers:
1. Schema validation (Pandera)
2. Business rules (DuckDB)
3. Pipeline contracts (pre/post conditions)
"""

import polars as pl
import pandera.polars as pap
import duckdb

from schema_validation import orders_schema


def validate_orders_pipeline(raw_path: str, output_path: str) -> pl.DataFrame:
    """
    Full quality pipeline with three tiers

    Args:
        raw_path: Path to raw CSV file
        output_path: Path for validated output Parquet

    Returns:
        Validated DataFrame

    Raises:
        ValueError: If critical validations fail
    """

    # 1. Load raw
    df = pl.read_csv(raw_path)
    print(f"Loaded {len(df):,} rows")

    # 2. Tier 1: Schema validation
    try:
        df = orders_schema.validate(df, lazy=True)
        print("[OK] Schema validation passed")
    except Exception as e:
        print(f"[FAIL] Schema validation failed: {e}")
        raise

    # 3. Tier 2: Business rules (DuckDB)
    con = duckdb.connect("analytics.duckdb")
    con.execute("CREATE TABLE IF NOT EXISTS temp_orders AS SELECT * FROM df")

    # Run checks from SQL file
    con.execute(open("quality/orders_checks.sql").read())

    failures = con.execute("""
        SELECT check_name, failing_rows
        FROM quality_log
        WHERE run_at > NOW() - INTERVAL '1 minute'
        AND failing_rows > 0
    """).fetchall()

    if failures:
        critical = [f for f in failures if f[0] in ["orphan_orders", "future_orders"]]
        if critical:
            raise ValueError(f"Critical checks failed: {critical}")
        print(f"[WARNING] Warnings: {failures}")

    # 4. Clean and transform
    clean_df = df.with_columns([
        pl.col("amount").round(2),
        pl.col("order_date").cast(pl.Date),
        pl.col("status").str.to_lowercase().str.strip(),
    ])

    # 5. Tier 3: Pipeline contract
    def check_no_data_loss(before: pl.DataFrame, after: pl.DataFrame) -> bool:
        return len(after) >= len(before) * 0.99

    if not check_no_data_loss(df, clean_df):
        raise ValueError("Lost >1% of rows during cleaning")

    # 6. Write validated output
    clean_df.write_parquet(output_path, compression="zstd")
    print(f"[OK] Wrote {len(clean_df):,} validated rows to {output_path}")

    return clean_df


if __name__ == "__main__":
    # Example usage
    validate_orders_pipeline(
        "raw/orders_2024_10.csv",
        "staging/orders/2024_10.parquet"
    )
