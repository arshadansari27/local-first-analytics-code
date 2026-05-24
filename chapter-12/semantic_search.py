"""Semantic search over the ``sensor_embeddings`` table built by
``embed_sensor_logs.py``.

Uses the DuckDB ``vss`` extension (HNSW + ``array_cosine_distance``) when
available, otherwise falls back to a pure-NumPy cosine similarity scan.
"""

import os
import sys
from typing import List, Tuple

import duckdb
import numpy as np

EMBED_MODEL = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
EMBED_DIM = 384


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
    return SentenceTransformer(EMBED_MODEL)


def _cosine_similarity(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _try_enable_vss(con: duckdb.DuckDBPyConnection) -> bool:
    try:
        con.execute("INSTALL vss;")
        con.execute("LOAD vss;")
        return True
    except Exception as e:  # noqa: BLE001 - extension may not be available
        print(f"VSS extension not available ({e}); using NumPy fallback.", file=sys.stderr)
        return False


def _ensure_hnsw_index(con: duckdb.DuckDBPyConnection, verbose: bool = True) -> bool:
    """Create an HNSW index with cosine metric if missing.

    Silently returns False on read-only connections (which is expected when
    this function is called from a process that opened the DB read-only).
    """
    try:
        # Allow HNSW indexes to persist across sessions
        con.execute("SET hnsw_enable_experimental_persistence = true;")
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_sensor_embeddings_hnsw "
            "ON sensor_embeddings USING HNSW (embedding) "
            "WITH (metric = 'cosine');"
        )
        return True
    except Exception as e:  # noqa: BLE001
        msg = str(e).lower()
        if "read-only" in msg:
            return False
        if verbose:
            print(
                f"Could not create HNSW index ({e}); using sequential scan.",
                file=sys.stderr,
            )
        return False


def semantic_search(
    query: str,
    top_k: int = 10,
    con: "duckdb.DuckDBPyConnection | None" = None,
) -> List[Tuple]:
    """Find sensor events similar to ``query``.

    Returns a list of tuples:
        (sensor_id, device_type, timestamp, status, temperature, pressure,
         searchable_text, similarity)
    where ``similarity`` is cosine similarity in [-1, 1] (higher is better).

    Pass ``con`` to reuse an existing DuckDB connection (avoids the
    "Can't open a connection ... with a different configuration" error
    when this is called from another module that already opened the DB).
    """
    if con is None and not os.path.exists("sensors.db"):
        print(
            "sensors.db not found. Run embed_sensor_logs.py first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    model = _load_model()
    qv = model.encode([query], convert_to_numpy=True).astype(np.float32)[0]

    if con is None:
        con = duckdb.connect("sensors.db", read_only=True)

    # Verify the embeddings table exists
    has_table = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'sensor_embeddings'"
    ).fetchone()[0]
    if not has_table:
        print(
            "Table sensor_embeddings not found. Run embed_sensor_logs.py first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    vss_ok = _try_enable_vss(con)
    if vss_ok:
        # Best-effort; query works without the index too.
        _ensure_hnsw_index(con)
        try:
            rows = con.execute(
                f"""
                SELECT sensor_id, device_type, timestamp, status,
                       temperature, pressure, searchable_text,
                       array_cosine_distance(embedding, ?::FLOAT[{EMBED_DIM}]) AS distance
                FROM sensor_embeddings
                ORDER BY distance ASC
                LIMIT ?
                """,
                [qv.tolist(), top_k],
            ).fetchall()
            # cosine distance = 1 - cosine similarity
            return [(*r[:-1], 1.0 - float(r[-1])) for r in rows]
        except Exception as e:  # noqa: BLE001
            print(f"VSS query failed ({e}); using NumPy fallback.", file=sys.stderr)

    # Fallback: compute in Python
    rows = con.execute(
        """
        SELECT sensor_id, device_type, timestamp, status,
               temperature, pressure, searchable_text, embedding
        FROM sensor_embeddings
        """
    ).fetchall()

    scored = []
    for row in rows:
        *fields, emb = row
        scored.append((*fields, _cosine_similarity(qv, emb)))
    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    res = semantic_search("pump running too hot", top_k=5)
    print("Query: 'pump running too hot'\n")
    for sensor_id, device, ts, status, temp, pressure, text, score in res:
        print(f"Score: {score:.3f}\n{text}\n")
