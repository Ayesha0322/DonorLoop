"""
agent/db_utils.py
Small shared helper so orchestrator.py, outreach.py, and escalation.py
all talk to the same SQLite DB the same way.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402


def get_connection():
    """Returns a sqlite3 connection with row access by column name."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_request(request_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM requests WHERE request_id = ?", (request_id,)
    ).fetchone()
    conn.close()
    return row


def get_all_donors():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM donors").fetchall()
    conn.close()
    return rows


def update_request_status(request_id: int, status: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE requests SET status = ? WHERE request_id = ?",
        (status, request_id),
    )
    conn.commit()
    conn.close()