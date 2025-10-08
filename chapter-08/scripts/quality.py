#!/usr/bin/env python3
"""
Quality checks for orchestration pipeline.

Validates that curated data meets expectations.
"""

import polars as pl
from pathlib import Path
import sys


def check_file_exists(path: Path) -> bool:
    """Check if file exists."""
    if not path.exists():
        print(f"[FAIL] File not found: {path}")
        return False
    print(f"[OK] File exists: {path}")
    return True


def check_row_count(path: Path, min_rows: int = 1) -> bool:
    """Check if file has minimum number of rows."""
    df = pl.read_parquet(path)
    row_count = len(df)

    if row_count < min_rows:
        print(f"[FAIL] {path} has {row_count} rows, expected at least {min_rows}")
        return False

    print(f"[OK] {path} has {row_count:,} rows")
    return True


def check_no_nulls(path: Path, column: str) -> bool:
    """Check if column has no null values."""
    df = pl.read_parquet(path)

    if column not in df.columns:
        print(f"[FAIL] {path} missing column: {column}")
        return False

    null_count = df[column].null_count()

    if null_count > 0:
        print(f"[FAIL] {path} column {column} has {null_count} nulls")
        return False

    print(f"[OK] {path} column {column} has no nulls")
    return True


def main():
    """Run all quality checks."""
    checks_passed = []

    # Check daily metrics
    metrics_path = Path("data/curated/daily_metrics.parquet")
    checks_passed.append(check_file_exists(metrics_path))

    if metrics_path.exists():
        checks_passed.append(check_row_count(metrics_path, min_rows=1))
        checks_passed.append(check_no_nulls(metrics_path, "date"))

    # Summary
    total = len(checks_passed)
    passed = sum(checks_passed)

    print(f"\n{'='*60}")
    print(f"Quality Checks: {passed}/{total} passed")
    print(f"{'='*60}")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
