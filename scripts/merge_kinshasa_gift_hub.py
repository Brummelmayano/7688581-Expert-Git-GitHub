"""Merge utility for importing data exported from kinshasa-gift-hub.

Expected JSON structure:
{
  "products": [{"id": "...", "name": "...", "price": 25, "currency": "USD", "description": "...", "image": "..."}],
  "gift_codes": [{"product_id": "...", "code": "..."}]
}
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_gift_codes(db_path: Path, payload: dict[str, Any]) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    codes = payload.get("gift_codes", [])

    conn = sqlite3.connect(db_path)
    try:
        for item in codes:
            try:
                conn.execute(
                    "INSERT INTO gift_codes (product_id, code, created_at, is_used) VALUES (?, ?, datetime('now'), 0)",
                    (item["product_id"], item["code"]),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()
    finally:
        conn.close()

    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import gift codes exported from kinshasa-gift-hub")
    parser.add_argument("--db", default="giftcards.db", help="SQLite database path")
    parser.add_argument("--input", required=True, help="Path to kinshasa-gift-hub export JSON")
    args = parser.parse_args()

    payload = load_payload(Path(args.input))
    inserted, skipped = merge_gift_codes(Path(args.db), payload)
    print(f"Import terminé: {inserted} codes insérés, {skipped} ignorés (doublons).")


if __name__ == "__main__":
    main()
