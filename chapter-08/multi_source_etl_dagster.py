#!/usr/bin/env python3
"""
Multi-Source ETL Pipeline - Dagster Version

Demonstrates asset-centric thinking with type-safe schemas.
"""

from dagster import asset, AssetExecutionContext, Definitions, MetadataValue
from dagster_duckdb import DuckDBResource
import polars as pl
import pandera.polars as pa
from pathlib import Path


# Define schemas
class CustomerSchema(pa.DataFrameModel):
    customer_id: int = pa.Field(unique=True, ge=1)
    email: str = pa.Field(str_matches=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    name: str
    updated_at: pl.Datetime


class OrderSchema(pa.DataFrameModel):
    order_id: int = pa.Field(unique=True, ge=1)
    customer_id: int = pa.Field(ge=1)
    total: float = pa.Field(ge=0.0)
    order_date: pl.Datetime


# Assets
@asset(
    group_name="ingestion",
    compute_kind="sftp"
)
def raw_customers(context: AssetExecutionContext) -> None:
    """Fetch customers from SFTP server."""
    import paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("sftp.example.com", username="user", password="pass")

    sftp = ssh.open_sftp()
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    sftp.get("/data/customers.csv", "data/raw/customers.csv")
    sftp.close()
    ssh.close()

    context.log.info("Downloaded customers.csv from SFTP")


@asset(
    group_name="ingestion",
    compute_kind="api"
)
def raw_orders(context: AssetExecutionContext) -> None:
    """Paginate through orders API."""
    import httpx, json

    all_orders = []
    page = 1

    while True:
        response = httpx.get(
            "https://api.example.com/orders",
            params={"page": page, "per_page": 1000}
        )
        response.raise_for_status()

        orders = response.json().get("orders", [])
        if not orders:
            break

        all_orders.extend(orders)
        page += 1

    Path("data/raw").mkdir(parents=True, exist_ok=True)
    with open("data/raw/orders.json", 'w') as f:
        json.dump(all_orders, f)

    context.log.info(f"Fetched {len(all_orders)} orders")


@asset(
    group_name="ingestion",
    compute_kind="minio"
)
def raw_inventory(context: AssetExecutionContext) -> None:
    """Download inventory from MinIO."""
    from minio import Minio

    client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    client.fget_object("data-lake", "inventory/latest.parquet", "data/raw/inventory.parquet")

    context.log.info("Downloaded inventory from MinIO")


@asset(
    deps=[raw_customers],
    compute_kind="polars",
    metadata={"schema": "CustomerSchema"}
)
def cleaned_customers(context: AssetExecutionContext) -> pl.DataFrame:
    """Deduplicate and validate customers."""

    df = pl.read_csv("data/raw/customers.csv")

    # Dedup
    df = df.sort("updated_at", descending=True).unique(subset=["customer_id"], keep="first")

    # Validate schema
    validated_df = CustomerSchema.validate(df)

    # Save
    Path("data/staging").mkdir(parents=True, exist_ok=True)
    validated_df.write_parquet("data/staging/customers.parquet")

    context.add_output_metadata({
        "num_rows": len(validated_df),
        "num_duplicates_removed": len(df) - len(validated_df)
    })

    return validated_df


@asset(
    deps=[raw_orders, cleaned_customers],
    compute_kind="polars"
)
def cleaned_orders(context: AssetExecutionContext) -> pl.DataFrame:
    """Join orders with customers, validate totals."""

    orders = pl.read_json("data/raw/orders.json")
    customers = pl.read_parquet("data/staging/customers.parquet")

    df = orders.join(customers.select(["customer_id", "name"]), on="customer_id", how="left")

    # Validate
    validated_df = OrderSchema.validate(df.select(list(OrderSchema.__annotations__.keys())))

    # Save
    Path("data/staging").mkdir(parents=True, exist_ok=True)
    df.write_parquet("data/staging/orders.parquet")

    context.add_output_metadata({
        "num_orders": len(df),
        "total_revenue": float(df["total"].sum()),
        "revenue_chart": MetadataValue.md(f"![Revenue](data:image/png;base64,...)")  # Add chart
    })

    return df


@asset(
    deps=[cleaned_orders],
    compute_kind="duckdb"
)
def daily_revenue(context: AssetExecutionContext, duckdb: DuckDBResource) -> None:
    """Compute daily revenue metrics."""

    with duckdb.get_connection() as conn:
        Path("data/curated").mkdir(parents=True, exist_ok=True)
        conn.execute("""
            COPY (
                SELECT
                    DATE_TRUNC('day', order_date) as date,
                    COUNT(*) as order_count,
                    COUNT(DISTINCT customer_id) as unique_customers,
                    SUM(total) as total_revenue
                FROM read_parquet('data/staging/orders.parquet')
                GROUP BY 1
                ORDER BY 1 DESC
            ) TO 'data/curated/daily_revenue.parquet' (FORMAT PARQUET)
        """)

    context.log.info("Daily revenue computed")


# Definitions
defs = Definitions(
    assets=[raw_customers, raw_orders, raw_inventory, cleaned_customers, cleaned_orders, daily_revenue],
    resources={"duckdb": DuckDBResource(database="data/analytics.duckdb")}
)


if __name__ == "__main__":
    from dagster import materialize

    # `daily_revenue` requires the `duckdb` resource.
    result = materialize(
        [raw_customers, raw_orders, raw_inventory, cleaned_customers, cleaned_orders, daily_revenue],
        resources={"duckdb": DuckDBResource(database="data/analytics.duckdb")},
    )

    if result.success:
        print("[OK] All assets materialized successfully")
    else:
        print("[FAIL] Asset materialization failed")
