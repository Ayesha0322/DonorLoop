"""
data/load_donors.py
Loads data/synthetic_donors.csv into the donors table.

This is now the ONE source of truth for donor data - run this instead of
having donor INSERTs living inside seed.sql, so there's no duplication
between the Faker-generated pool and hand-written seed rows.

Run:
    python data/load_donors.py
"""

import csv
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import config  # noqa: E402

CSV_PATH = Path(__file__).resolve().parent / "synthetic_donors.csv"


def load_donors(clear_existing: bool = True) -> int:
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()

    if clear_existing:
        # donors is referenced by outreach_log via FK, so wipe dependents too
        # if you're resetting the whole demo dataset from scratch
        cur.execute("DELETE FROM donors")
        # donors uses AUTOINCREMENT, so without this, IDs would keep climbing
        # (201, 401, ...) on every re-run instead of restarting at 1 - which
        # breaks seed.sql's hardcoded donor_id references in outreach_log
        cur.execute("DELETE FROM sqlite_sequence WHERE name='donors'")

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (r["name"], r["blood_type"], r["city"],
             float(r["latitude"]), float(r["longitude"]),
             r["phone"], r["last_donation_date"])
            for r in reader
        ]

    cur.executemany(
        """INSERT INTO donors
           (name, blood_type, city, latitude, longitude, phone, last_donation_date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    total = load_donors()
    print(f"Loaded donors table: {total} rows now in donors")
