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


# ===== Pattern 2: dvc.lock for Reproducible Pipelines =====
#
# DVC 3.x has no `dvc lock` command. Instead, `dvc repro` automatically
# writes/updates `dvc.lock` with the checksums of every stage's deps,
# params, and outs. Commit `dvc.lock` alongside `dvc.yaml` so anyone
# can reproduce the exact pipeline state.

dvc repro            # runs the pipeline and writes dvc.lock
git add dvc.yaml dvc.lock
git commit -m "Lock pipeline for release v1.2"

# To freeze a stage so `dvc repro` won't re-run it even if deps change:
# dvc freeze <stage_name>
# dvc unfreeze <stage_name>


# ===== Common Patterns =====

# Track partitioned directories
dvc add data/raw/sales/
# Creates sales.dvc pointing to a directory containing:
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
