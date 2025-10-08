#!/bin/bash
# DVC Remote Storage Configuration
# Chapter 10: Version Control for Data

# Option 1: Local directory (NAS, external drive)
dvc remote add -d backup /mnt/nas/dvc-cache

# Option 2: MinIO (local S3)
dvc remote add -d minio s3://dvc-bucket/cache
dvc remote modify minio endpointurl http://localhost:9000

# Push data to remote
dvc push

# Later, pull on different machine
dvc pull
