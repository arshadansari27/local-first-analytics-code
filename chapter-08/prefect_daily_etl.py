"""
Level 2: Prefect Flow
Chapter 8: Orchestration Progression

Daily ETL flow with automatic retries, caching, and parallel execution.
"""

from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta
import polars as pl
import duckdb
import httpx


@task(
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1)
)
def extract_api_data(endpoint: str) -> str:
    """Fetch data with automatic retries."""
    response = httpx.get(endpoint, timeout=30.0)
    response.raise_for_status()

    output_path = f"data/raw/{endpoint.split('/')[-1]}.json"
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
    """Example: Retry strategy for flaky APIs with exponential backoff."""
    response = httpx.get(url)
    if response.status_code == 429:  # Rate limit
        raise Exception("Rate limited")
    return response.json()


@flow
def parallel_ingestion():
    """Example: Parallel execution of multiple tasks."""
    # Submit all tasks at once
    futures = []
    for source in ["users", "events", "products", "orders"]:
        future = extract_api_data.submit(f"https://api.example.com/{source}")
        futures.append(future)

    # Wait for all to complete
    results = [f.result() for f in futures]

    # Now transform in parallel
    parquet_files = transform_to_parquet.map(results)


if __name__ == "__main__":
    daily_etl_flow()
