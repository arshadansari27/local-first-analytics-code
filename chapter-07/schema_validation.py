"""
Chapter 7: Schema Validation with Pandera

This module demonstrates Tier 1 validation: schema validation using Pandera
to catch structural issues, type errors, and value range violations.
"""

import pandera as pa
import pandera.polars as pap
import polars as pl


# Schema for an e-commerce orders table
orders_schema = pap.DataFrameSchema({
    "order_id": pap.Column(pl.Utf8, unique=True, nullable=False),
    "customer_id": pap.Column(pl.Int64, nullable=False),
    "order_date": pap.Column(pl.Date, nullable=False),
    "amount": pap.Column(
        pl.Float64,
        checks=[
            pap.Check.greater_than(0),
            pap.Check.less_than(1_000_000)  # flag whales separately
        ]
    ),
    "quantity": pap.Column(
        pl.Int32,
        checks=[
            pap.Check.greater_than_or_equal_to(1),
            pap.Check.less_than_or_equal_to(100)  # bulk orders go elsewhere
        ]
    ),
    "status": pap.Column(
        pl.Utf8,
        checks=pap.Check.isin(["pending", "shipped", "delivered", "cancelled"])
    ),
})


def validate_orders(csv_path: str) -> pl.DataFrame:
    """
    Validate orders CSV against schema.

    Args:
        csv_path: Path to CSV file

    Returns:
        Validated DataFrame

    Raises:
        SchemaErrors: If validation fails
    """
    df = pl.read_csv(csv_path)

    try:
        validated_df = orders_schema.validate(df, lazy=True)
        print(f"[OK] Validated {len(validated_df):,} rows")
        return validated_df
    except pa.errors.SchemaErrors as e:
        print("[FAIL] Validation failed:")
        print(e.failure_cases)  # Shows exactly which rows/columns failed
        raise


if __name__ == "__main__":
    # Example usage
    # df = validate_orders("raw/orders_2024_10.csv")

    # Demo with synthetic data
    demo_df = pl.DataFrame({
        "order_id": ["O001", "O002", "O003"],
        "customer_id": [1, 2, 3],
        "order_date": ["2024-10-01", "2024-10-02", "2024-10-03"],
        "amount": [100.50, 250.75, 50.25],
        "quantity": [2, 1, 5],
        "status": ["pending", "shipped", "delivered"]
    })

    try:
        validated = orders_schema.validate(demo_df, lazy=True)
        print(f"[OK] Demo validation passed: {len(validated)} rows")
    except pa.errors.SchemaErrors as e:
        print(f"[FAIL] Demo validation failed: {e}")
