#!/usr/bin/env python3
"""
Multi-Source ETL Pipeline - Prefect Version

Demonstrates parallel extraction with retries and caching.
"""

from prefect import flow, task
from prefect.cache_policies import INPUTS
from datetime import timedelta
import httpx
import polars as pl
import duckdb
from pathlib import Path


@task(retries=3, retry_delay_seconds=60)
def fetch_customers_sftp() -> str:
    """Download customers CSV from SFTP."""
    import paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("sftp.example.com", username="user", password="pass")

    sftp = ssh.open_sftp()
    sftp.get("/data/customers.csv", "data/raw/customers.csv")
    sftp.close()
    ssh.close()

    return "data/raw/customers.csv"


@task(retries=5, retry_delay_seconds=[10, 30, 60, 300, 600])
def fetch_orders_api() -> str:
    """Paginate through orders API."""

    all_orders = []
    page = 1

    while True:
        response = httpx.get(
            "https://api.example.com/orders",
            params={"page": page, "per_page": 1000},
            timeout=30.0
        )

        if response.status_code == 429:
            raise Exception("Rate limited")

        response.raise_for_status()
        orders = response.json().get("orders", [])

        if not orders:
            break

        all_orders.extend(orders)
        page += 1

    output_path = "data/raw/orders.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    import json
    with open(output_path, 'w') as f:
        json.dump(all_orders, f)

    return output_path


@task(retries=3, retry_delay_seconds=30)
def fetch_inventory_minio() -> str:
    """Download inventory from MinIO."""
    from minio import Minio

    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )

    client.fget_object(
        "data-lake",
        "inventory/latest.parquet",
        "data/raw/inventory.parquet"
    )

    return "data/raw/inventory.parquet"


@task(cache_policy=INPUTS, cache_expiration=timedelta(hours=24))
def clean_customers(customers_csv: str) -> str:
    """Deduplicate and validate customers."""

    df = pl.read_csv(customers_csv)

    # Dedup by customer_id, keep most recent
    df = df.sort("updated_at", descending=True).unique(subset=["customer_id"], keep="first")

    # Validate
    assert df["customer_id"].is_duplicated().sum() == 0, "Duplicate customer IDs found"
    assert df["email"].is_null().sum() == 0, "Null emails found"

    output_path = "data/staging/customers.parquet"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)

    return output_path


@task
def clean_orders(orders_json: str, customers_parquet: str) -> str:
    """Join orders with customers, validate totals."""

    orders = pl.read_json(orders_json)
    customers = pl.read_parquet(customers_parquet)

    # Join
    df = orders.join(customers, on="customer_id", how="left")

    # Validate order totals
    df = df.with_columns(
        (pl.col("line_items").list.eval(pl.element().struct.field("price") * pl.element().struct.field("quantity")).list.sum()).alias("calculated_total")
    )

    mismatches = (df["total"] - df["calculated_total"]).abs() > 0.01
    assert mismatches.sum() == 0, f"Found {mismatches.sum()} orders with total mismatches"

    output_path = "data/staging/orders.parquet"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)

    return output_path


@task
def snapshot_inventory(inventory_parquet: str) -> str:
    """Filter to positive quantities only."""

    df = pl.read_parquet(inventory_parquet)
    df = df.filter(pl.col("quantity") >= 0)

    output_path = "data/staging/inventory.parquet"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_path)

    return output_path


@task
def compute_revenue(orders_parquet: str) -> str:
    """Aggregate daily revenue in DuckDB."""

    conn = duckdb.connect()

    conn.execute(f"""
        COPY (
            SELECT
                DATE_TRUNC('day', order_date) as date,
                COUNT(*) as order_count,
                COUNT(DISTINCT customer_id) as unique_customers,
                SUM(total) as total_revenue
            FROM read_parquet('{orders_parquet}')
            GROUP BY 1
        ) TO 'data/curated/daily_revenue.parquet' (FORMAT PARQUET)
    """)

    return "data/curated/daily_revenue.parquet"


@flow(name="multi-source-etl", log_prints=True)
def multi_source_etl_flow():
    """Main pipeline with parallel extraction."""

    # Extract in parallel (Prefect runs these concurrently)
    customers_future = fetch_customers_sftp.submit()
    orders_future = fetch_orders_api.submit()
    inventory_future = fetch_inventory_minio.submit()

    # Wait and clean
    customers_clean = clean_customers(customers_future.result())
    orders_clean = clean_orders(orders_future.result(), customers_clean)
    inventory_clean = snapshot_inventory(inventory_future.result())

    # Compute metrics
    revenue = compute_revenue(orders_clean)

    print(f"[OK] Pipeline complete. Revenue at {revenue}")


if __name__ == "__main__":
    multi_source_etl_flow()
