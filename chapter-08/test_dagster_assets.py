#!/usr/bin/env python3
"""
Tests for Dagster assets.

Demonstrates testing without execution.
"""

import pytest
import polars as pl
from pathlib import Path
from dagster import materialize


def test_cleaned_events_schema():
    """Verify schema is enforced."""
    from dagster_pipeline import CleanedEventsSchema

    # Create bad test data
    bad_df = pl.DataFrame({
        "user_id": [None, 2, 3],  # Nulls should fail
        "event_type": ["click", "invalid", "view"],  # "invalid" should fail
        "timestamp": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "amount": [10.0, 20.0, 30.0]
    })

    # This should raise ValidationError
    with pytest.raises(Exception) as exc_info:
        CleanedEventsSchema.validate(bad_df)

    assert "user_id" in str(exc_info.value) or "event_type" in str(exc_info.value)


def test_full_pipeline_with_sample():
    """Run entire pipeline on 100-row sample."""
    from dagster_pipeline import raw_events_asset, cleaned_events_asset, daily_metrics_asset

    # Generate synthetic data
    sample = pl.DataFrame({
        "user_id": range(1, 101),
        "event_type": ["click"] * 50 + ["view"] * 50,
        "timestamp": ["2024-01-01T10:00:00"] * 100,
        "amount": [10.0] * 100
    })

    Path("data/raw").mkdir(parents=True, exist_ok=True)
    sample.write_json("data/raw/events.json")

    # Materialize all assets
    result = materialize([raw_events_asset, cleaned_events_asset, daily_metrics_asset])

    assert result.success

    # Check outputs
    assert Path("data/curated/daily_metrics.parquet").exists()
    metrics = pl.read_parquet("data/curated/daily_metrics.parquet")
    assert len(metrics) > 0


def test_asset_dependencies():
    """Verify asset dependency graph."""
    from dagster_pipeline import defs

    assets = defs.get_asset_graph()
    asset_keys = [key.to_user_string() for key in assets.all_asset_keys]

    # Check all assets exist
    assert "raw_events" in asset_keys or "raw_events_asset" in asset_keys
    assert "cleaned_events" in asset_keys or "cleaned_events_asset" in asset_keys
    assert "daily_metrics" in asset_keys or "daily_metrics_asset" in asset_keys


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
