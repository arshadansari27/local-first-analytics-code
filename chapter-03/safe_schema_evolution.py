"""
Safe schema evolution patterns from Chapter 3.

When new files gain a column that older files lack, readers (DuckDB,
Polars, PyArrow) will surface NULL for the missing rows. That's fine
for many queries, but pipelines are often easier to reason about when
the column is *materialized* with an explicit default value.
"""

import polars as pl


def add_column_with_default(df: pl.DataFrame, column: str, default: str) -> pl.DataFrame:
    """
    GOOD: Materialize the new column with an explicit default.

    Works whether or not the column already exists:
      - missing column -> create it filled with `default`
      - existing column with nulls -> fill the nulls with `default`
    """
    if column not in df.columns:
        return df.with_columns(pl.lit(default).alias(column))
    return df.with_columns(pl.col(column).fill_null(default))


def add_column_as_new_type(df: pl.DataFrame, source: str, new_name: str, dtype: pl.DataType) -> pl.DataFrame:
    """
    GOOD: Need a different type? Add a NEW column and migrate readers.
    Leaves the original column untouched so old consumers keep working.
    """
    return df.with_columns(pl.col(source).cast(dtype).alias(new_name))


def unsafe_type_change(_: pl.DataFrame) -> pl.DataFrame:
    """
    BAD: Silently changing an existing column's type breaks readers
    that pin the old schema, and breaks `union_by_name` reads across
    files where the same column has two different types.

    Don't do this. Use `add_column_as_new_type` instead.
    """
    raise NotImplementedError("Don't change column types in place - add a new column instead")


if __name__ == "__main__":
    # Old data: column does not exist yet.
    df_old = pl.DataFrame({"user_id": [1, 2, 3], "revenue": [100, 200, 150]})
    print("Old data (pre-evolution):")
    print(df_old)

    print("\nAfter backfilling with default for new `referral_source` column:")
    print(add_column_with_default(df_old, "referral_source", "unknown"))

    # New data: column exists but some rows are null.
    df_new = pl.DataFrame({
        "user_id": [4, 5, 6],
        "revenue": [180, 220, 190],
        "referral_source": [None, "google", None],
    })
    print("\nNew data (partial nulls):")
    print(df_new)

    print("\nAfter filling nulls with default:")
    print(add_column_with_default(df_new, "referral_source", "unknown"))

    print("\nAdding a wider-typed copy of `revenue` (int -> float):")
    print(add_column_as_new_type(df_new, "revenue", "revenue_f64", pl.Float64))
