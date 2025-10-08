#!/bin/bash
# DVC + Git Integration Patterns
# Chapter 10: Version Control for Data

# ===== Pattern 1: DVC + Git Tags =====

# After completing Q4 report
dvc add data/raw/*.parquet
git add data/raw/*.dvc etl/ dvc.yaml
git commit -m "Q4 2024 report data and pipeline"
git tag -a q4-2024 -m "Quarterly report Q4"

# Push both
git push origin main --tags
dvc push

# Reproduce Q4 report anytime:
git checkout q4-2024
dvc checkout
dvc repro  # Exact same results


# ===== Pattern 2: Lock Files for Pipelines =====

# Generate lock file with exact data versions
dvc lock dvc.yaml

# This creates dvc.lock with checksums:
# - Input data hashes
# - Code hashes
# - Output hashes

# Commit dvc.lock -> anyone can reproduce exactly
git add dvc.lock
git commit -m "Lock pipeline for release v1.2"


# ===== Common Patterns =====

# Track partitioned directories
dvc add data/raw/sales/
# Creates sales.dvc pointing to directory with:
# - sales/2024-01/*.parquet
# - sales/2024-02/*.parquet
# ...

# Use .dvcignore for temporary files
echo "data/temp/" >> .dvcignore

# Always push after adding
dvc add data/raw/sales.parquet
git add data/raw/sales.parquet.dvc
git commit -m "New sales data"
git push
dvc push  # Don't forget this!
