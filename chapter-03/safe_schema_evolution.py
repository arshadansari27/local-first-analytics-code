"""
Safe schema evolution pattern from Chapter 3
"""

import polars as pl


# Example: Adding a column with a default value
def add_column_safely(df: pl.DataFrame) -> pl.DataFrame:
    """
    GOOD: Add column with explicit default
    This ensures old data has a consistent value instead of NULL
    """
    return df.with_columns(
        pl.col("referral_source").fill_null("unknown")  # explicit default
    )


# BAD EXAMPLE - DON'T DO THIS
def unsafe_type_change(df: pl.DataFrame) -> pl.DataFrame:
    """
    BAD: Changing int -> float breaks old readers
    Instead, create a new column if you need a different type
    """
    # DON'T: df.with_columns(pl.col("count").cast(pl.Float64))
    # DO: df.with_columns(pl.col("count").alias("count_float").cast(pl.Float64))
    raise NotImplementedError("Don't change column types - create new columns instead")


if __name__ == "__main__":
    # Example usage
    df = pl.DataFrame({"user_id": [1, 2, 3], "revenue": [100, 200, 150], "referral_source": [None, "google", None]})

    print("Original DataFrame:")
    print(df)

    print("\nAfter adding default for referral_source:")
    df_with_default = add_column_safely(df)
    print(df_with_default)
