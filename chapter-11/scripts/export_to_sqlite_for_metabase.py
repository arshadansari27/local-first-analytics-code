#!/usr/bin/env python3
"""
Export DuckDB to SQLite for Metabase.

Metabase doesn't natively support DuckDB, so we export to SQLite format.
"""

import duckdb
from pathlib import Path


def export_duckdb_to_sqlite():
    """Export DuckDB database to SQLite for Metabase compatibility."""

    duckdb_path = 'data/curated/analytics.duckdb'
    sqlite_export_dir = 'data/curated/metabase_export'

    # Check if DuckDB file exists
    if not Path(duckdb_path).exists():
        print(f"[ERROR] DuckDB file not found: {duckdb_path}")
        print("[INFO] Create the DuckDB database first with your ETL pipeline")
        return

    print(f"[INFO] Exporting {duckdb_path} to SQLite...")

    # Connect and export
    con = duckdb.connect(duckdb_path)

    # Export entire database to SQLite format
    con.execute(f"EXPORT DATABASE '{sqlite_export_dir}' (FORMAT SQLITE);")

    print(f"[OK] Exported to {sqlite_export_dir}")
    print(f"[OK] Use {sqlite_export_dir}.db in Metabase")


if __name__ == "__main__":
    export_duckdb_to_sqlite()
