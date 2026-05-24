#!/usr/bin/env python3
"""
Tests for Dagster assets.

Demonstrates testing assets in isolation, without running the orchestrator.
"""

import pytest
import polars as pl
from pathlib import Path
from dagster import materialize


def test_cleaned_events_schema():
    """Verify the Pandera schema is enforced (any failure is fine here)."""
    from dagster_pipeline import CleanedEventsSchema

    # Bad rows: a null user_id and an invalid event_type.
    import datetime as _dt
    bad_df = pl.DataFrame({
        "user_id": [None, 2, 3],
        "event_type": ["click", "invalid", "view"],
        "event_ts": [
            _dt.datetime(2024, 1, 1),
            _dt.datetime(2024, 1, 2),
            _dt.datetime(2024, 1, 3),
        ],
        "amount": [10.0, 20.0, 30.0],
    })

    # The schema should reject this DataFrame for at least one reason.
    with pytest.raises(Exception):
        CleanedEventsSchema.validate(bad_df)


def test_full_pipeline_with_sample():
    """Run the full asset graph on a 100-row synthetic sample."""
    from dagster_pipeline import raw_events, cleaned_events, daily_metrics
    from dagster_duckdb import DuckDBResource

    # Generate synthetic data — the raw_events asset reads from this path.
    sample = pl.DataFrame({
        "user_id": list(range(1, 101)),
        "event_type": ["click"] * 50 + ["view"] * 50,
        "timestamp": ["2024-01-01T10:00:00"] * 100,
        "amount": [10.0] * 100,
    })

    Path("data/raw").mkdir(parents=True, exist_ok=True)
    Path("data/staging").mkdir(parents=True, exist_ok=True)
    Path("data/curated").mkdir(parents=True, exist_ok=True)
    sample.write_parquet("data/raw/events.parquet")

    result = materialize(
        [raw_events, cleaned_events, daily_metrics],
        resources={"duckdb": DuckDBResource(database="data/analytics.duckdb")},
    )

    assert result.success
    assert Path("data/curated/daily_metrics.parquet").exists()
    metrics = pl.read_parquet("data/curated/daily_metrics.parquet")
    assert len(metrics) > 0


def test_asset_dependencies():
    """Verify the asset dependency graph contains the expected nodes."""
    from dagster_pipeline import defs

    # Dagster's ``Definitions.resolve_asset_graph()`` returns an AssetGraph
    # with ``all_asset_keys``. (``get_asset_graph`` was renamed.)
    asset_graph = defs.resolve_asset_graph()
    asset_keys = {key.to_user_string() for key in asset_graph.get_all_asset_keys()}

    assert "raw_events" in asset_keys
    assert "cleaned_events" in asset_keys
    assert "daily_metrics" in asset_keys


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
