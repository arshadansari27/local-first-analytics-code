#!/usr/bin/env python3
"""
Fetch orders from paginated API.

Example script for Chapter 8 orchestration patterns.
"""

import httpx
import json
from pathlib import Path

API_BASE = "https://api.example.com"
OUTPUT = Path("data/raw/orders.json")


def main():
    """Fetch all pages of orders from API."""
    all_orders = []
    page = 1

    print(f"Fetching orders from {API_BASE}...")

    while True:
        try:
            response = httpx.get(
                f"{API_BASE}/orders",
                params={"page": page, "per_page": 1000},
                timeout=30.0
            )
            response.raise_for_status()

            data = response.json()
            orders = data.get("orders", [])

            if not orders:
                break

            all_orders.extend(orders)
            print(f"  Fetched page {page}: {len(orders)} orders")
            page += 1

        except httpx.HTTPError as e:
            print(f"[ERROR] HTTP error on page {page}: {e}")
            raise

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(all_orders, indent=2))

    print(f"[OK] Fetched {len(all_orders)} orders total")
    print(f"[OK] Saved to {OUTPUT}")


if __name__ == "__main__":
    main()
