#!/usr/bin/env python3
"""
Prefect flow example for ingesting sales data.

Example from Chapter 9: Docker Compose + Dev Containers
"""

from prefect import flow, task
import duckdb


@task
def extract_data():
    """Extract data from CSV files."""
    return duckdb.query("SELECT * FROM read_csv('data/raw/*.csv')").df()


@task
def transform_data(df):
    """Filter data for high-value transactions."""
    return df[df['amount'] > 100]


@task
def load_to_parquet(df):
    """Save to Parquet format."""
    df.to_parquet('data/curated/sales.parquet')
    return len(df)


@flow(name="Ingest Sales Data")
def ingest_pipeline():
    """Main ETL pipeline."""
    df = extract_data()
    clean = transform_data(df)
    count = load_to_parquet(clean)
    return count


if __name__ == "__main__":
    ingest_pipeline()
