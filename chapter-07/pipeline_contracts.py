"""
Chapter 7: Pipeline Contracts

This module demonstrates Tier 3 validation: pipeline contracts with pre/post conditions
to ensure transformations work correctly and don't lose data.
"""

from dataclasses import dataclass
from typing import Callable, List, Tuple
import polars as pl


@dataclass
class DataContract:
    """Pre and post-conditions for a transformation"""
    name: str
    pre_conditions: list[Callable]
    post_conditions: list[Callable]


def check_row_count_positive(df: pl.DataFrame) -> bool:
    """Basic sanity check"""
    return len(df) > 0


def check_no_nulls_in_key(df: pl.DataFrame, key: str) -> bool:
    """Ensure key column has no nulls"""
    return df[key].null_count() == 0


def check_revenue_increase(df_before: pl.DataFrame, df_after: pl.DataFrame) -> bool:
    """Total revenue shouldn't decrease during aggregation"""
    before_total = df_before["amount"].sum()
    after_total = df_after["revenue"].sum()
    return after_total >= before_total * 0.99  # allow 1% rounding


# Define contract
aggregate_contract = DataContract(
    name="daily_revenue_aggregation",
    pre_conditions=[
        lambda df: check_row_count_positive(df),
        lambda df: check_no_nulls_in_key(df, "order_id"),
    ],
    post_conditions=[
        lambda df: check_row_count_positive(df),
        lambda df: check_no_nulls_in_key(df, "date"),
        lambda df: (df["revenue"] >= 0).all(),  # no negative daily revenue
    ]
)


def run_with_contract(
    contract: DataContract,
    transform: Callable,
    df: pl.DataFrame
) -> pl.DataFrame:
    """Execute transform with pre/post validation"""

    # Pre-conditions
    for i, check in enumerate(contract.pre_conditions):
        if not check(df):
            raise ValueError(f"{contract.name}: pre-condition {i} failed")

    # Transform
    result = transform(df)

    # Post-conditions
    for i, check in enumerate(contract.post_conditions):
        if not check(result):
            raise ValueError(f"{contract.name}: post-condition {i} failed")

    return result


# Example transform
def aggregate_daily_revenue(df: pl.DataFrame) -> pl.DataFrame:
    return df.group_by("order_date").agg([
        pl.col("amount").sum().alias("revenue"),
        pl.col("order_id").count().alias("order_count"),
    ])


# Quality Level Implementation
class QualityLevel:
    CRITICAL = "critical"  # Stop pipeline
    WARNING = "warning"    # Log but continue
    INFO = "info"          # Record for analysis


def validate_with_policy(
    df: pl.DataFrame,
    checks: dict[str, tuple[Callable, str]]
) -> pl.DataFrame:
    """Run checks with different failure policies"""

    issues = []

    for check_name, (check_fn, level) in checks.items():
        try:
            if not check_fn(df):
                issues.append((check_name, level))
        except Exception as e:
            issues.append((check_name, QualityLevel.CRITICAL))
            print(f"[FAIL] Check {check_name} crashed: {e}")

    # Handle by severity
    critical = [name for name, lvl in issues if lvl == QualityLevel.CRITICAL]
    warnings = [name for name, lvl in issues if lvl == QualityLevel.WARNING]

    if critical:
        raise ValueError(f"Critical quality failures: {critical}")

    if warnings:
        print(f"[WARNING] Quality warnings: {warnings}")

    return df


if __name__ == "__main__":
    # Example usage with demo data
    orders_df = pl.DataFrame({
        "order_id": ["O001", "O002", "O003"],
        "order_date": ["2024-10-01", "2024-10-01", "2024-10-02"],
        "amount": [100.50, 250.75, 50.25]
    })

    try:
        daily_revenue = run_with_contract(
            aggregate_contract,
            aggregate_daily_revenue,
            orders_df
        )
        print("[OK] Contract validation passed")
        print(daily_revenue)
    except ValueError as e:
        print(f"[FAIL] Contract validation failed: {e}")
