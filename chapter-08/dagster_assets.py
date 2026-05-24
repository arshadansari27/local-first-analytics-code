"""
Level 3: Dagster Asset-Based Pipeline
Chapter 8: Orchestration Progression

Asset-oriented pipeline with type safety and data lineage.
"""

from dagster import asset, AssetExecutionContext, Definitions, MetadataValue
from dagster_duckdb import DuckDBResource
import polars as pl
import pandera.polars as pa
from pathlib import Path
import httpx


# Define schemas with Pandera
class CleanedEventsSchema(pa.DataFrameModel):
    user_id: int = pa.Field(ge=1)
    event_type: str = pa.Field(isin=["click", "view", "purchase"])
    event_ts: pl.Datetime
    amount: float = pa.Field(ge=0.0)

    class Config:
        strict = True
        coerce = True


@asset(
    group_name="ingestion",
    compute_kind="polars",
    metadata={
        "partition_by": "date",
        "expected_rows": 1_000_000
    }
)
def raw_events(context: AssetExecutionContext) -> pl.DataFrame:
    """Extract events from API and save as Parquet."""

    # Fetch data (with your retry logic)
    response = httpx.get("https://api.example.com/events")
    data = response.json()

    df = pl.DataFrame(data)

    # Save to disk
    output_path = Path("data/raw/events.parquet")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)

    context.log.info(f"Extracted {len(df)} rows to {output_path}")

    return df


@asset(
    deps=[raw_events],  # Runs after raw_events materializes
    compute_kind="polars"
)
def cleaned_events(context: AssetExecutionContext) -> pl.DataFrame:
    """Validate and clean raw events."""

    df = pl.read_parquet("data/raw/events.parquet")

    # Apply business rules
    df = (
        df
        .filter(pl.col("user_id").is_not_null())
        .filter(pl.col("event_type").is_in(["click", "view", "purchase"]))
        .with_columns([
            pl.col("timestamp").str.to_datetime().alias("event_ts"),
            pl.col("amount").cast(pl.Float64).fill_null(0.0)
        ])
    )

    # Save cleaned version
    output_path = Path("data/staging/events.parquet")
    df.write_parquet(output_path)

    context.log.info(f"Cleaned {len(df)} events ({len(df)/pl.read_parquet('data/raw/events.parquet').height*100:.1f}% pass rate)")

    return df


@asset(
    deps=[cleaned_events],
    compute_kind="duckdb"
)
def daily_metrics(context: AssetExecutionContext, duckdb: DuckDBResource) -> None:
    """Compute aggregated metrics in DuckDB."""

    with duckdb.get_connection() as conn:
        conn.execute("""
            COPY (
                SELECT
                    DATE_TRUNC('day', event_ts) as date,
                    event_type,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    SUM(amount) as total_amount
                FROM read_parquet('data/staging/events.parquet')
                GROUP BY 1, 2
            ) TO 'data/curated/daily_metrics.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)

    context.log.info("Metrics computed and saved")


@asset
def cleaned_events_v2(context: AssetExecutionContext) -> pl.DataFrame:
    """Returns validated DataFrame or fails."""

    df = pl.read_parquet("data/raw/events.parquet")

    # Transform
    df = (df
        .filter(pl.col("user_id").is_not_null())
        .with_columns(pl.col("timestamp").str.to_datetime().alias("event_ts"))
    )

    # Validate against schema
    validated_df = CleanedEventsSchema.validate(df)

    context.log.info(f"[OK] Schema validation passed for {len(validated_df)} rows")

    return validated_df


# Definitions — wire assets to resources.
defs = Definitions(
    assets=[raw_events, cleaned_events, daily_metrics],
    resources={
        "duckdb": DuckDBResource(database="data/analytics.duckdb"),
    },
)
