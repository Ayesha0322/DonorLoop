"""
DonorLoop - NLP Database Writer

Processes a free-text blood request using the NLP pipeline
and saves the structured request into the shared SQLite database.
"""

import sqlite3
import sys
from pathlib import Path

# Add the DonorLoop project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_PATH
from nlp.extract import process_request


def save_request(text: str) -> int:
    """
    Process a free-text request and save it to the requests table.

    Returns:
        The newly created request_id.
    """

    result = process_request(text)

    required_fields = [
        "blood_type",
        "units_needed",
        "hospital",
        "hospital_latitude",
        "hospital_longitude",
        "urgency",
    ]

    missing = [
        field
        for field in required_fields
        if result.get(field) is None
    ]

    if missing:
        raise ValueError(
            f"Could not extract required fields: {', '.join(missing)}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO requests (
                raw_text,
                blood_type,
                units_needed,
                hospital,
                hospital_latitude,
                hospital_longitude,
                urgency,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                result["raw_text"],
                result["blood_type"],
                result["units_needed"],
                result["hospital"],
                result["hospital_latitude"],
                result["hospital_longitude"],
                result["urgency"],
                "open",
            ),
        )

        request_id = cursor.lastrowid
        conn.commit()

        return request_id

    finally:
        conn.close()


if __name__ == "__main__":

    sample = (
        "Urgent! We need 2 units of O+ blood at "
        "Shifa Hospital Islamabad immediately."
    )

    request_id = save_request(sample)

    print("\nRequest successfully saved!")
    print(f"request_id: {request_id}")

    conn = sqlite3.connect(DB_PATH)

    row = conn.execute(
        """
        SELECT
            request_id,
            blood_type,
            units_needed,
            hospital,
            urgency,
            status
        FROM requests
        WHERE request_id = ?
        """,
        (request_id,),
    ).fetchone()

    conn.close()

    print("\nDatabase record:")
    print(row)
