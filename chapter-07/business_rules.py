"""
Chapter 7: Business Rules Validation

This module demonstrates Tier 2 validation: business logic validation using DuckDB
to check referential integrity, statistical outliers, and temporal logic.
"""

import duckdb
import polars as pl


def run_quality_checks(db_path: str = "analytics.duckdb") -> pl.DataFrame:
    """
    Run business rules quality checks on orders data.

    Args:
        db_path: Path to DuckDB database

    Returns:
        DataFrame with failing checks

    Raises:
        ValueError: If critical checks fail
    """
    con = duckdb.connect(db_path)

    # Load fresh data
    con.execute("""
        CREATE OR REPLACE TABLE staging.orders AS
        SELECT * FROM read_parquet('staging/orders/*.parquet')
    """)

    # Run quality checks
    con.execute(open("quality/orders_checks.sql").read())

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
            raise ValueError(f"Critical quality checks failed: {critical_failures}")
        else:
            print("[WARNING] Non-critical issues logged, continuing pipeline")

    return failures


if __name__ == "__main__":
    # Example usage
    try:
        failures = run_quality_checks()
        if len(failures) == 0:
            print("[OK] All quality checks passed")
    except ValueError as e:
        print(f"[FAIL] {e}")
        raise
