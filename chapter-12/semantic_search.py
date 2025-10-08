import duckdb
import numpy as np
from typing import List, Tuple
from llama_index.embeddings.ollama import OllamaEmbedding


def cosine_similarity(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _try_enable_vss(con: duckdb.DuckDBPyConnection) -> bool:
    try:
        con.execute("INSTALL vss;")
        con.execute("LOAD vss;")
        return True
    except Exception:
        return False


def _ensure_vss_index(con: duckdb.DuckDBPyConnection) -> bool:
    """Try to create a VSS index if not present. Returns True if SQL path usable."""
    try:
        # Attempt to create or ensure an index on the embeddings column.
        # Syntax may vary across versions; try a common pattern.
        con.execute("CREATE INDEX IF NOT EXISTS idx_sensor_embeddings_vss ON sensor_embeddings(embedding) USING vss;")
        return True
    except Exception:
        return False


def semantic_search(query: str, top_k: int = 10) -> List[Tuple]:
    """Find sensor events similar to query.

    Tries DuckDB VSS extension first (cosine similarity in SQL). Falls back to Python.
    """
    embed_model = OllamaEmbedding(model_name="nomic-embed-text")
    con = duckdb.connect("sensors.db", read_only=False)

    qv = embed_model.get_text_embedding(query)

    # Preferred: DuckDB VSS
    if _try_enable_vss(con) and _ensure_vss_index(con):
        try:
            con.register("qv", np.array(qv, dtype=float))
            rows = con.execute(
                """
                SELECT sensor_id, device_type, timestamp, status, temperature, pressure, searchable_text,
                       vss_distance(embedding, qv) AS distance
                FROM sensor_embeddings
                ORDER BY distance ASC
                LIMIT ?
                """,
                [top_k],
            ).fetchall()
            # Convert distance to similarity (cosine distance ~ 1 - cosine_sim)
            results = []
            for r in rows:
                *fields, dist = r
                sim = 1.0 - float(dist)
                results.append((*fields, sim))
            return results
        except Exception:
            # Fall back if vss SQL path not supported in current DuckDB
            pass

    # Fallback: compute similarities in Python
    rows = con.execute(
        """
        SELECT sensor_id, device_type, timestamp, status, temperature, pressure, searchable_text, embedding
        FROM sensor_embeddings
        """
    ).fetchall()

    scored = []
    for row in rows:
        *fields, emb = row
        sim = cosine_similarity(qv, emb)
        scored.append((*fields, sim))
    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    res = semantic_search("pump running too hot", top_k=5)
    print("Query: 'pump running too hot'\n")
    for sensor_id, device, ts, status, temp, pressure, text, score in res:
        print(f"Score: {score:.3f}\n{text}\n")

