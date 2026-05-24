"""
Chapter 7: Business Rules Validation

This module demonstrates Tier 2 validation: business logic validation using DuckDB
to check referential integrity, statistical outliers, and temporal logic.
"""

import random
from datetime import date, timedelta
from pathlib import Path

import duckdb
import polars as pl

CHECKS_SQL = Path(__file__).parent / "quality" / "orders_checks.sql"


def _seed_staging(con: duckdb.DuckDBPyConnection) -> None:
    """Create a ``staging`` schema with synthetic orders + customers.

    Keeps the example self-contained — in a real pipeline these tables would
    be populated from upstream Parquet (e.g. ``read_parquet('staging/orders/*.parquet')``).
    """
    random.seed(42)
    customers = pl.DataFrame({"id": list(range(1, 51))})

    orders = pl.DataFrame([
        {
            "order_id": f"O{i:04d}",
            # Mix of valid customer ids (1..50) plus a few orphans (>50) to
            # exercise the referential-integrity check.
            "customer_id": random.choice(list(range(1, 50)) + [999]),
            "order_date": date(2024, 10, 1) + timedelta(days=random.randint(0, 30)),
            "amount": round(random.uniform(10, 500), 2),
            "quantity": random.randint(1, 10),
            "status": random.choice(["pending", "shipped", "delivered"]),
        }
        for i in range(1, 101)
    ])

    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    con.register("_customers_df", customers)
    con.register("_orders_df", orders)
    con.execute("CREATE OR REPLACE TABLE staging.customers AS SELECT * FROM _customers_df")
    con.execute("CREATE OR REPLACE TABLE staging.orders    AS SELECT * FROM _orders_df")


def run_quality_checks(db_path: str = ":memory:") -> pl.DataFrame:
    """
    Run business rules quality checks on orders data.

    Args:
        db_path: Path to DuckDB database (defaults to in-memory for the demo)

    Returns:
        DataFrame with failing checks

    Raises:
        ValueError: If critical checks fail
    """
    con = duckdb.connect(db_path)
    _seed_staging(con)

    # Run quality checks from the SQL file
    con.execute(CHECKS_SQL.read_text())

    # Review failures
    failures = con.execute("""
        SELECT
            check_name,
            failing_rows,
            run_at
        FROM quality_log
        WHERE failing_rows > 0
        ORDER BY run_at DESC
        LIMIT 10
    """).pl()

    if len(failures) > 0:
        print("[WARNING] Quality issues detected:")
        print(failures)

        # Decide: fail or warn
        critical_checks = ["orphan_orders", "future_orders"]
        critical_failures = failures.filter(
            pl.col("check_name").is_in(critical_checks)
        )

        if len(critical_failures) > 0:
            print("[FAIL] Critical quality checks failed (demo only — not raising):")
            print(critical_failures)
        else:
            print("[WARNING] Non-critical issues logged, continuing pipeline")

    return failures


if __name__ == "__main__":
    failures = run_quality_checks()
    if len(failures) == 0:
        print("[OK] All quality checks passed")
    else:
        print(f"[OK] Quality run complete — {len(failures)} check(s) reported failing rows")
