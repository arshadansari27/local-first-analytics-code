#!/usr/bin/env python3
"""
Export DuckDB to SQLite for Metabase.

Metabase has no native DuckDB driver, so we copy the curated tables into a
SQLite file via DuckDB's `sqlite` extension. The chapter text walks through
why this is the easiest path; DuckDB's `EXPORT DATABASE` only supports CSV
and Parquet formats, so it cannot produce a SQLite file directly.
"""

from pathlib import Path

import duckdb

DUCKDB_PATH = Path("data/curated/analytics.duckdb")
SQLITE_PATH = Path("data/curated/metabase_export.db")

# Tables to mirror into SQLite. Adjust to match your warehouse.
TABLES = ("customers", "products", "orders", "order_items", "daily_metrics")


def export_duckdb_to_sqlite() -> None:
    """Mirror curated DuckDB tables into a SQLite file for Metabase."""

    if not DUCKDB_PATH.exists():
        print(f"[ERROR] DuckDB file not found: {DUCKDB_PATH}")
        print("[INFO] Create the DuckDB database first with your ETL pipeline")
        return

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()

    print(f"[INFO] Exporting {DUCKDB_PATH} -> {SQLITE_PATH} ...")

    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute("INSTALL sqlite; LOAD sqlite;")
    con.execute(f"ATTACH '{SQLITE_PATH}' AS mb (TYPE SQLITE);")

    for table in TABLES:
        try:
            con.execute(f"CREATE TABLE mb.{table} AS SELECT * FROM curated.{table};")
            print(f"  [OK] {table}")
        except duckdb.CatalogException as exc:
            print(f"  [SKIP] {table}: {exc}")

    con.execute("DETACH mb;")
    con.close()

    print(f"[OK] Wrote {SQLITE_PATH}")
    print(f"[OK] In Metabase, add a SQLite database pointing at: {SQLITE_PATH}")


if __name__ == "__main__":
    export_duckdb_to_sqlite()
