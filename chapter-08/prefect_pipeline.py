#!/usr/bin/env python3
"""
Prefect Daily ETL Flow - Level 2 Orchestration

Demonstrates:
- Automatic retries with backoff
- Task result caching
- Parallel execution
- Local-first (no cloud required)
"""

from prefect import flow, task
from prefect.cache_policies import INPUTS
from datetime import timedelta
import polars as pl
import duckdb
from pathlib import Path


@task(
    retries=3,
    retry_delay_seconds=60,
    cache_policy=INPUTS,
    cache_expiration=timedelta(hours=1)
)
def extract_api_data(endpoint: str) -> str:
    """Fetch data with automatic retries."""
    import httpx

    response = httpx.get(endpoint, timeout=30.0)
    response.raise_for_status()

    output_path = f"data/raw/{endpoint.split('/')[-1]}.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(response.text)

    return output_path


@task
def transform_to_parquet(json_path: str) -> str:
    """Convert JSON to Parquet with Polars."""
    df = pl.read_json(json_path)

    # Clean and validate
    df = df.filter(pl.col("user_id").is_not_null())
    df = df.with_columns(pl.col("timestamp").str.to_datetime())

    output_path = json_path.replace("raw", "staging").replace(".json", ".parquet")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path, compression="zstd")

    return output_path


@task
def compute_metrics(staging_path: str) -> str:
    """Run DuckDB aggregations."""
    conn = duckdb.connect()

    query = f"""
    COPY (
        SELECT
            DATE_TRUNC('day', timestamp) as date,
            COUNT(DISTINCT user_id) as dau,
            COUNT(*) as events
        FROM read_parquet('{staging_path}')
        GROUP BY 1
    ) TO 'data/curated/daily_metrics.parquet' (FORMAT PARQUET)
    """

    Path("data/curated").mkdir(parents=True, exist_ok=True)
    conn.execute(query)
    return "data/curated/daily_metrics.parquet"


@flow(name="daily-etl", log_prints=True)
def daily_etl_flow():
    """Main pipeline with dependency graph."""

    # These run in parallel (Prefect handles it)
    users_json = extract_api_data("https://api.example.com/users")
    events_json = extract_api_data("https://api.example.com/events")

    # Wait for both, then transform
    users_parquet = transform_to_parquet(users_json)
    events_parquet = transform_to_parquet(events_json)

    # Compute metrics from transformed data
    metrics = compute_metrics(events_parquet)

    print(f"[OK] Pipeline complete. Metrics at {metrics}")


@task(retries=5, retry_delay_seconds=[10, 30, 60, 300, 600])
def fetch_rate_limited_api(url: str):
    """Fetch from API with exponential backoff for rate limits."""
    import httpx

    # Prefect will retry with exponential backoff
    response = httpx.get(url, timeout=30.0)
    if response.status_code == 429:  # Rate limit
        raise Exception("Rate limited")
    response.raise_for_status()
    return response.json()


@flow
def parallel_ingestion():
    """Submit multiple tasks at once for parallel execution."""
    futures = []
    for source in ["users", "events", "products", "orders"]:
        future = extract_api_data.submit(f"https://api.example.com/{source}")
        futures.append(future)

    # Wait for all to complete
    results = [f.result() for f in futures]

    # Now transform in parallel
    parquet_files = transform_to_parquet.map(results)

    return parquet_files


def create_deployment():
    """Serve the flow on a cron schedule (Prefect 3.x).

    In Prefect 3, ``Deployment.build_from_flow`` was removed. The simplest
    local-first replacement is ``flow.serve(...)``, which blocks the current
    process and polls for scheduled runs (no separate worker/agent needed).
    For deployments that target a work pool, use ``flow.deploy(...)``.
    """
    daily_etl_flow.serve(
        name="daily-etl-prod",
        cron="0 6 * * *",
        timezone="America/New_York",
    )


if __name__ == "__main__":
    # Run flow directly
    daily_etl_flow()
