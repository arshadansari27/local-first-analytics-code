"""Embed sensor readings into a DuckDB table for semantic search.

Uses sentence-transformers (no external server required). The default model
``all-MiniLM-L6-v2`` produces 384-dim FLOAT vectors and is ~80 MB on first run.
The embeddings are stored as ``FLOAT[384]`` so they are directly usable by the
DuckDB ``vss`` extension (HNSW + cosine distance).
"""

import os
import sys

import duckdb
import numpy as np
import pandas as pd
from tqdm import tqdm

EMBED_MODEL = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
EMBED_DIM = 384  # all-MiniLM-L6-v2 -> 384 dims


def create_searchable_text(row: pd.Series) -> str:
    return (
        f"{row['device_type']} sensor {row['sensor_id']} at {row['facility']}: "
        f"status {row['status']}, temp {row['temperature']}°C, "
        f"pressure {row['pressure']} PSI, vibration {row['vibration']} mm/s"
    )


def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(
            "sentence-transformers is not installed. Install with:\n"
            "  pip install sentence-transformers",
            file=sys.stderr,
        )
        raise SystemExit(1) from e
    print(f"Loading embedding model '{EMBED_MODEL}' (downloads ~80MB on first run)...")
    return SentenceTransformer(EMBED_MODEL)


def main():
    parquet_glob = "data/sensors/**/*.parquet"
    if not any(True for _ in __import__("glob").iglob("data/sensors/**/*.parquet", recursive=True)):
        print(
            "No parquet files found under data/sensors/. "
            "Run: python code/chapter-12/generate_sensor_data.py",
            file=sys.stderr,
        )
        raise SystemExit(1)

    model = _load_model()

    con = duckdb.connect("sensors.db")
    df = con.execute(
        f"""
        SELECT *
        FROM read_parquet('{parquet_glob}')
        WHERE status != 'normal'
        USING SAMPLE 100000 ROWS
        """
    ).fetchdf()

    if df.empty:
        print("No interesting (non-'normal') rows found. Nothing to embed.")
        return

    texts = [create_searchable_text(row) for _, row in df.iterrows()]

    print(f"Generating embeddings for {len(texts)} rows...")
    # encode handles batching internally; show_progress_bar gives a tqdm-like UI
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    ).astype(np.float32)

    if embeddings.shape[1] != EMBED_DIM:
        print(
            f"Warning: model produced {embeddings.shape[1]}-dim vectors, "
            f"expected {EMBED_DIM}. Update EMBED_DIM and semantic_search.py.",
            file=sys.stderr,
        )

    df["searchable_text"] = texts
    # Store as a python list of FLOAT, DuckDB will infer FLOAT[N]
    df["embedding"] = list(embeddings)

    con.execute("DROP TABLE IF EXISTS sensor_embeddings")
    con.register("tmp_df", df)
    # Cast embedding to FLOAT[N] so the vss extension can index it
    con.execute(
        f"""
        CREATE TABLE sensor_embeddings AS
        SELECT
            * EXCLUDE (embedding),
            embedding::FLOAT[{EMBED_DIM}] AS embedding
        FROM tmp_df
        """
    )
    con.unregister("tmp_df")
    n = con.execute("SELECT COUNT(*) FROM sensor_embeddings").fetchone()[0]
    print(f"Created table sensor_embeddings with {n} rows in sensors.db")


if __name__ == "__main__":
    main()
