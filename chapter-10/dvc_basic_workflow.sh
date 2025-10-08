#!/bin/bash
# DVC Basic Workflow
# Chapter 10: Version Control for Data

# Install DVC
pip install dvc

# Initialize in your project
cd local-analytics-project/
git init
dvc init

# DVC creates .dvc/ directory and updates .gitignore

# 1. Add raw data to DVC tracking
dvc add data/raw/sales.parquet

# This creates sales.parquet.dvc (metadata file) and adds:
# - sales.parquet to .gitignore (Git won't track the file)
# - sales.parquet.dvc to Git (Git tracks the pointer)

# 2. Commit the metadata
git add data/raw/sales.parquet.dvc .gitignore
git commit -m "Track sales data v1"

# 3. Later, update the data
# (e.g., new ingestion run creates new sales.parquet)
dvc add data/raw/sales.parquet
git add data/raw/sales.parquet.dvc
git commit -m "Sales data - Q4 update"

# Reproduce a specific commit
# Teammate wants to reproduce your Q3 report
git checkout <q3-commit-hash>
dvc checkout  # Pulls the exact data versions from that commit

# Now data/ matches the exact state from Q3
python etl/transform.py  # Identical results
