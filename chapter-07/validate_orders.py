"""
Chapter 7: Complete Quality Pipeline

Full end-to-end quality validation pipeline combining all three tiers:
1. Schema validation (Pandera)
2. Business rules (DuckDB)
3. Pipeline contracts (pre/post conditions)
"""

import random
from datetime import date, timedelta
from pathlib import Path

import duckdb
import polars as pl

from schema_validation import orders_schema

HERE = Path(__file__).parent
CHECKS_SQL = HERE / "quality" / "orders_checks.sql"


def _ensure_sample_csv(raw_path: Path, n_rows: int = 100) -> None:
    """Generate a small synthetic orders CSV if one doesn't exist yet.

    Keeps the script runnable on a fresh checkout without external data.
    """
    if raw_path.exists():
        return
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    random.seed(7)
    rows = [
        {
            "order_id": f"O{i:04d}",
            "customer_id": random.randint(1, 50),
            "order_date": (date(2024, 10, 1) + timedelta(days=random.randint(0, 30))).isoformat(),
            "amount": round(random.uniform(10, 500), 2),
            "quantity": random.randint(1, 10),
            "status": random.choice(["pending", "shipped", "delivered"]),
        }
        for i in range(1, n_rows + 1)
    ]
    pl.DataFrame(rows).write_csv(raw_path)


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
    raw = Path(raw_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _ensure_sample_csv(raw)

    # 1. Load raw — let polars parse dates, then coerce quantity to Int32
    #    so the dtype matches what ``orders_schema`` expects.
    df = pl.read_csv(raw, try_parse_dates=True).with_columns(
        pl.col("quantity").cast(pl.Int32),
    )
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
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    # Register the validated polars frame and seed a minimal customers table
    # so the orphan-order check has something to join against.
    con.register("_orders_df", df)
    con.execute("CREATE OR REPLACE TABLE staging.orders AS SELECT * FROM _orders_df")
    con.execute(
        "CREATE OR REPLACE TABLE staging.customers AS "
        "SELECT DISTINCT customer_id AS id FROM staging.orders"
    )

    # Run checks from SQL file
    con.execute(CHECKS_SQL.read_text())

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
        pl.col("status").str.to_lowercase().str.strip_chars(),
    ])

    # 5. Tier 3: Pipeline contract
    def check_no_data_loss(before: pl.DataFrame, after: pl.DataFrame) -> bool:
        return len(after) >= len(before) * 0.99

    if not check_no_data_loss(df, clean_df):
        raise ValueError("Lost >1% of rows during cleaning")

    # 6. Write validated output
    clean_df.write_parquet(out, compression="zstd")
    print(f"[OK] Wrote {len(clean_df):,} validated rows to {out}")

    return clean_df


if __name__ == "__main__":
    # Example usage — paths are relative to this file so it runs from any cwd.
    validate_orders_pipeline(
        str(HERE / "raw" / "orders_2024_10.csv"),
        str(HERE / "staging" / "orders" / "2024_10.parquet"),
    )
