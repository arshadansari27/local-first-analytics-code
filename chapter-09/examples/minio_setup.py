#!/usr/bin/env python3
"""
Create MinIO bucket and test S3 connectivity.

Example from Chapter 9: Docker Compose + Dev Containers
"""

from minio import Minio


def create_bucket(bucket_name: str = "analytics"):
    """Create MinIO bucket if it doesn't exist."""
    client = Minio(
        'minio:9000',
        access_key='minioadmin',
        secret_key='minioadmin',
        secure=False
    )

    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        print(f'[OK] Bucket "{bucket_name}" created')
    else:
        print(f'[OK] Bucket "{bucket_name}" already exists')


if __name__ == "__main__":
    create_bucket()
