#!/usr/bin/env python3
"""
Financial Reconciliation with Polars

Matches bank transactions with internal ledger entries using:
- Fuzzy matching on timestamps (tolerance window)
- Anti-joins to find unmatched records
- Validation rules for data quality
"""

import polars as pl
from datetime import datetime
from typing import List, Tuple
from pathlib import Path


def prepare_for_matching(df: pl.DataFrame, id_col: str) -> pl.DataFrame:
    """
    Normalize data for fuzzy matching.

    Args:
        df: Input dataframe
        id_col: ID column name (not used but kept for consistency)

    Returns:
        DataFrame with match keys added
    """
    return df.with_columns([
        # Round amount to cents (avoid float precision issues)
        (pl.col("amount") * 100).round(0).cast(pl.Int64).alias("amount_cents"),
        # Extract date for exact day matching
        pl.col("timestamp").dt.date().alias("date"),
        # Time as seconds since midnight (for fuzzy match).
        # dt.hour/minute/second return Int8 in Polars 1.x. Multiplying
        # by 3600 silently overflows Int16 (max 32767) for any hour >= 9,
        # so cast to Int32 first.
        (
            pl.col("timestamp").dt.hour().cast(pl.Int32) * 3600 +
            pl.col("timestamp").dt.minute().cast(pl.Int32) * 60 +
            pl.col("timestamp").dt.second().cast(pl.Int32)
        ).alias("time_seconds")
    ])


def match_transactions(
    bank_df: pl.DataFrame,
    ledger_df: pl.DataFrame,
    time_tolerance_seconds: int = 60
) -> pl.DataFrame:
    """
    Match bank transactions with ledger entries using fuzzy timestamp matching.

    Args:
        bank_df: Bank transactions (prepared)
        ledger_df: Ledger entries (prepared)
        time_tolerance_seconds: Maximum time difference for match (default 60s)

    Returns:
        DataFrame with matched transactions
    """
    matches = (
        bank_df
        .join(
            ledger_df,
            on=["date", "amount_cents"],
            how="inner"
        )
        # Filter: timestamps within tolerance
        .filter(
            (pl.col("time_seconds") - pl.col("time_seconds_right")).abs() <= time_tolerance_seconds
        )
        .select([
            pl.col("bank_id"),
            pl.col("ledger_id"),
            pl.col("amount"),
            pl.col("timestamp").alias("bank_time"),
            pl.col("timestamp_right").alias("ledger_time"),
            (pl.col("timestamp") - pl.col("timestamp_right"))
              .dt.total_seconds()
              .alias("time_diff_seconds")
        ])
    )

    return matches


def find_unmatched(
    df: pl.DataFrame,
    matches: pl.DataFrame,
    id_col: str,
    status_label: str
) -> pl.DataFrame:
    """
    Find unmatched records using anti-join.

    Args:
        df: Source dataframe (bank or ledger)
        matches: Matched transactions
        id_col: ID column to join on
        status_label: Label for unmatched status

    Returns:
        DataFrame with unmatched records
    """
    cols = [c for c in df.columns if c not in ["date", "amount_cents", "time_seconds"]]

    unmatched = (
        df
        .join(matches, on=id_col, how="anti")
        .select(cols)
        .with_columns(pl.lit(status_label).alias("status"))
    )

    return unmatched


def validate_reconciliation(
    bank_df: pl.DataFrame,
    ledger_df: pl.DataFrame,
    matches_df: pl.DataFrame
) -> List[Tuple[str, bool, str]]:
    """
    Run validation rules on reconciliation results.

    Returns:
        List of (rule_name, passed, message) tuples
    """
    results = []

    # Rule 1: Bank-side and ledger-side totals of the matched pairs
    # must agree to within a cent. Pull each side from its *source*
    # frame (bank_df / ledger_df) — otherwise the rule is tautological.
    matched_bank_ids = matches_df.select("bank_id")
    matched_ledger_ids = matches_df.select("ledger_id")
    bank_matched_total = (
        bank_df.join(matched_bank_ids, on="bank_id", how="inner")
        .select(pl.col("amount").sum())[0, 0]
    )
    ledger_matched_total = (
        ledger_df.join(matched_ledger_ids, on="ledger_id", how="inner")
        .select(pl.col("amount").sum())[0, 0]
    )

    rule1_pass = abs(bank_matched_total - ledger_matched_total) < 0.01
    results.append((
        "Matched totals equal",
        rule1_pass,
        f"Bank: ${bank_matched_total:.2f} | Ledger: ${ledger_matched_total:.2f}"
    ))

    # Rule 2: No duplicate matches (one bank -> one ledger)
    bank_dups = (
        matches_df
        .group_by("bank_id")
        .agg(pl.len().alias("match_count"))
        .filter(pl.col("match_count") > 1)
    )

    rule2_pass = len(bank_dups) == 0
    results.append((
        "No duplicate bank matches",
        rule2_pass,
        f"Found {len(bank_dups)} duplicates" if not rule2_pass else "OK"
    ))

    # Rule 3: Match rate > 80%
    total_bank = len(bank_df)
    matched_bank = len(matches_df)
    match_rate = matched_bank / total_bank if total_bank > 0 else 0

    rule3_pass = match_rate >= 0.80
    results.append((
        "Match rate >= 80%",
        rule3_pass,
        f"{match_rate:.1%} ({matched_bank}/{total_bank})"
    ))

    # Rule 4: All matched timestamps within 5 minutes
    if len(matches_df) > 0:
        max_diff = matches_df.select(pl.col("time_diff_seconds").abs().max())[0, 0]
    else:
        max_diff = 0

    rule4_pass = max_diff <= 300
    results.append((
        "Time differences <= 5min",
        rule4_pass,
        f"Max: {max_diff:.0f}s"
    ))

    return results


def main():
    """Run financial reconciliation example."""

    # Create output directories
    Path("data/curated/reconciliation").mkdir(parents=True, exist_ok=True)
    Path("data/curated/validation").mkdir(parents=True, exist_ok=True)

    # Sample data: Bank transactions
    bank = pl.DataFrame({
        "bank_id": ["B001", "B002", "B003", "B004"],
        "amount": [1500.00, 2300.50, 890.25, 1500.00],
        "timestamp": [
            datetime(2024, 10, 1, 9, 15, 30),
            datetime(2024, 10, 1, 14, 22, 10),
            datetime(2024, 10, 2, 11, 5, 45),
            datetime(2024, 10, 2, 16, 30, 20),
        ],
        "description": ["Invoice #1234", "Payment XYZ", "Refund", "Invoice #1234"]
    })

    # Sample data: Internal ledger
    ledger = pl.DataFrame({
        "ledger_id": ["L001", "L002", "L003"],
        "amount": [1500.00, 2300.50, 995.00],
        "timestamp": [
            datetime(2024, 10, 1, 9, 16, 0),   # 30s diff
            datetime(2024, 10, 1, 14, 22, 15), # 5s diff
            datetime(2024, 10, 2, 10, 58, 30), # No match
        ],
        "reference": ["INV-1234", "PAY-XYZ", "SAL-995"]
    })

    print("=== Financial Reconciliation ===\n")

    # Step 1: Prepare data
    print("Step 1: Normalizing data...")
    bank_prep = prepare_for_matching(bank, "bank_id")
    ledger_prep = prepare_for_matching(ledger, "ledger_id")

    # Step 2: Match transactions
    print("Step 2: Matching transactions with 60s tolerance...")
    matches = match_transactions(bank_prep, ledger_prep, time_tolerance_seconds=60)
    print(f"  Found {len(matches)} matches\n")

    print("Matched transactions:")
    print(matches)
    print()

    # Step 3: Find unmatched
    print("Step 3: Finding unmatched records...")
    unmatched_bank = find_unmatched(bank_prep, matches, "bank_id", "UNMATCHED_BANK")
    unmatched_ledger = find_unmatched(ledger_prep, matches, "ledger_id", "UNMATCHED_LEDGER")

    print(f"\nUnmatched bank transactions ({len(unmatched_bank)}):")
    print(unmatched_bank)

    print(f"\nUnmatched ledger entries ({len(unmatched_ledger)}):")
    print(unmatched_ledger)
    print()

    # Step 4: Validate
    print("Step 4: Running validation rules...")
    validation_results = validate_reconciliation(bank, ledger, matches)

    print("\n=== VALIDATION RESULTS ===")
    for rule, passed, msg in validation_results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {rule}: {msg}")

    # Step 5: Write reports
    print("\nStep 5: Writing reconciliation reports...")

    # Combine all results
    # Ensure all amount columns are Float64 to avoid schema mismatch
    reconciliation_report = pl.concat([
        matches.with_columns(pl.lit("MATCHED").alias("status")),
        unmatched_bank.select([
            pl.col("bank_id"),
            pl.lit(None).cast(pl.String).alias("ledger_id"),
            pl.col("amount").cast(pl.Float64),
            pl.col("timestamp").alias("bank_time"),
            pl.lit(None).cast(pl.Datetime).alias("ledger_time"),
            pl.lit(None).cast(pl.Float64).alias("time_diff_seconds"),
            pl.col("status")
        ]),
        unmatched_ledger.select([
            pl.lit(None).cast(pl.String).alias("bank_id"),
            pl.col("ledger_id"),
            pl.col("amount").cast(pl.Float64),
            pl.lit(None).cast(pl.Datetime).alias("bank_time"),
            pl.col("timestamp").alias("ledger_time"),
            pl.lit(None).cast(pl.Float64).alias("time_diff_seconds"),
            pl.col("status")
        ])
    ], how="vertical_relaxed").sort("bank_time", "ledger_time", nulls_last=True)

    # Write to Parquet
    reconciliation_report.write_parquet(
        "data/curated/reconciliation/2024-10-01.parquet",
        compression="snappy"
    )

    # Write validation results
    validation_df = pl.DataFrame({
        "rule": [r[0] for r in validation_results],
        "passed": [r[1] for r in validation_results],
        "message": [r[2] for r in validation_results],
        "run_timestamp": [datetime.now()] * len(validation_results)
    })

    validation_df.write_parquet(
        "data/curated/validation/2024-10-01.parquet",
        compression="snappy"
    )

    print("[OK] Reconciliation report saved to data/curated/reconciliation/")
    print("[OK] Validation log saved to data/curated/validation/")


if __name__ == "__main__":
    main()
