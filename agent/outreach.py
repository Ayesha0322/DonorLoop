"""
agent/outreach.py
Drafts a personalized message per donor and "sends" it (logs to
outreach_log, prints to console, optional Twilio sandbox send).
"""

from datetime import datetime, timezone

import config
from db_utils import get_connection


def generate_message(donor: dict, request: dict) -> str:
    return (
        f"Hi {donor['name']}, this is DonorLoop. There's an urgent need for "
        f"{request['blood_type']} blood/platelets at {request['hospital']} "
        f"({request['urgency']} priority). You're a compatible donor "
        f"~{donor['distance_km']} km away and eligible to donate. "
        f"Can you help? Reply YES or NO."
    )


def send_message(donor: dict, request: dict, message: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO outreach_log (request_id, donor_id, message_sent, sent_at, response_status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (request["request_id"], donor["donor_id"], message,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()

    print(f"  -> [SIMULATED SMS to {donor['name']} ({donor['phone']})]: {message}")

    if config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
        _send_via_twilio_sandbox(donor["phone"], message)


def _send_via_twilio_sandbox(phone: str, message: str) -> None:
    try:
        from twilio.rest import Client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_="+15005550006", to=phone)
    except Exception as e:
        print(f"  [twilio] send failed (non-fatal for demo): {e}")


def contact_donors(donor_shortlist, request: dict):
    contacted = []
    for donor in donor_shortlist:
        message = generate_message(donor, request)
        send_message(donor, request, message)
        contacted.append(donor)
    return contacted