"""
agent/escalation.py
Response monitoring + autonomous escalation decision logic.
"""

import random
from datetime import datetime, timezone

from db_utils import get_connection

ESCALATION_ORDER = ["widen_radius", "relax_compatibility", "notify_blood_bank"]

REASONS = {
    "widen_radius": "Not enough donors confirmed within the initial radius; "
                     "widening the search area.",
    "relax_compatibility": "Still insufficient confirmations after widening radius; "
                            "relaxing to compatible (not just exact-match) blood types "
                            "under emergency protocol.",
    "notify_blood_bank": "Donor pool exhausted at current radius/compatibility "
                          "settings; notifying blood bank for backup supply.",
}


def count_confirmations(request_id: int, simulate: bool = False) -> int:
    conn = get_connection()

    if simulate:
        pending = conn.execute(
            "SELECT outreach_id FROM outreach_log "
            "WHERE request_id = ? AND response_status = 'pending'",
            (request_id,),
        ).fetchall()
        for row in pending:
            new_status = "confirmed" if random.random() < 0.3 else "declined"
            conn.execute(
                "UPDATE outreach_log SET response_status = ?, responded_at = ? "
                "WHERE outreach_id = ?",
                (new_status, datetime.now(timezone.utc).isoformat(), row["outreach_id"]),
            )
        conn.commit()

    confirmed = conn.execute(
        "SELECT COUNT(*) AS n FROM outreach_log "
        "WHERE request_id = ? AND response_status = 'confirmed'",
        (request_id,),
    ).fetchone()["n"]
    conn.close()
    return confirmed


def decide_next_action(already_used: set):
    for action in ESCALATION_ORDER:
        if action not in already_used:
            return action, REASONS[action]
    return None


def log_escalation(request_id: int, action: str, reason: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO escalation_log (request_id, action_taken, reason, triggered_at)
        VALUES (?, ?, ?, ?)
        """,
        (request_id, action, reason, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()