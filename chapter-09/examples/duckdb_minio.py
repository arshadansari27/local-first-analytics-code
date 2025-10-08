#!/usr/bin/env python3
"""
Query Parquet files from MinIO using DuckDB.

Example from Chapter 9: Docker Compose + Dev Containers
"""

import duckdb


def query_minio_parquet():
    """Configure DuckDB to query MinIO and run sample query."""

    # Configure S3 credentials for MinIO
    duckdb.execute("""
        INSTALL httpfs;
        LOAD httpfs;
        SET s3_endpoint='minio:9000';
        SET s3_access_key_id='minioadmin';
        SET s3_secret_access_key='minioadmin';
        SET s3_use_ssl=false;
        SET s3_url_style='path';
    """)

    print("[OK] DuckDB configured for MinIO")

    # Query Parquet from MinIO (after you upload files)
    try:
        df = duckdb.query("""
            SELECT * FROM read_parquet('s3://analytics/curated/sales/*.parquet')
            LIMIT 10
        """).df()
        print("\n[OK] Query results:")
        print(df)
    except Exception as e:
        print(f"[INFO] No data found in MinIO yet: {e}")
        print("[INFO] Upload Parquet files to s3://analytics/curated/sales/ first")


if __name__ == "__main__":
    query_minio_parquet()
