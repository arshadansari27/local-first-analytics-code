"""
Create Reference (Dimension) Tables
Creates small Parquet files for rate codes and payment types.
"""
import duckdb

con = duckdb.connect()

# Create reference data directory
from pathlib import Path
Path("data/raw/taxi").mkdir(parents=True, exist_ok=True)

# Create rate codes reference table
con.execute("""
    COPY (
        SELECT * FROM (VALUES
            (1, 'Standard rate'),
            (2, 'JFK'),
            (3, 'Newark'),
            (4, 'Nassau or Westchester'),
            (5, 'Negotiated fare'),
            (6, 'Group ride')
        ) AS t(rate_code_id, description)
    ) TO 'data/raw/taxi/rate_codes.parquet' (FORMAT PARQUET)
""")

print("[OK] Created rate_codes.parquet")

# Create payment types reference table
con.execute("""
    COPY (
        SELECT * FROM (VALUES
            (1, 'Credit card'),
            (2, 'Cash'),
            (3, 'No charge'),
            (4, 'Dispute'),
            (5, 'Unknown'),
            (6, 'Voided trip')
        ) AS t(payment_type_id, description)
    ) TO 'data/raw/taxi/payment_types.parquet' (FORMAT PARQUET)
""")

print("[OK] Created payment_types.parquet")

con.close()

print("\n[COMPLETE] Reference tables created in data/raw/taxi/")
