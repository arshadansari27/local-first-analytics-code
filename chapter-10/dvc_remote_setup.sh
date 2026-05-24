#!/bin/bash
# DVC Remote Storage Configuration
# Chapter 10: Version Control for Data
#
# For S3-compatible remotes (MinIO, AWS S3, etc.) you also need the
# S3 extra: `pip install 'dvc[s3]'` (or `pip install dvc-s3`).

# Option 1: Local directory (NAS, external drive)
dvc remote add -d backup /mnt/nas/dvc-cache

# Option 2: MinIO (local S3)
dvc remote add -d minio s3://dvc-bucket/cache
dvc remote modify minio endpointurl http://localhost:9000
dvc remote modify minio use_ssl false
# Credentials: prefer env vars (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)
# or `dvc remote modify --local minio access_key_id <key>` to keep secrets
# out of the committed config.

# Push data to remote
dvc push

# Later, pull on different machine
dvc pull
