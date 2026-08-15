import sqlite3
from pathlib import Path

import streamlit as st


# ============================================================
# DATABASE
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "donorloop.db"


def get_connection():
    """Connect to the project's SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# DATABASE QUERIES
# ============================================================

def get_summary():
    conn = get_connection()

    data = {
        "donors": conn.execute(
            "SELECT COUNT(*) FROM donors"
        ).fetchone()[0],

        "requests": conn.execute(
            "SELECT COUNT(*) FROM requests"
        ).fetchone()[0],

        "open": conn.execute(
            "SELECT COUNT(*) FROM requests WHERE status = 'open'"
        ).fetchone()[0],

        "resolved": conn.execute(
            "SELECT COUNT(*) FROM requests WHERE status = 'resolved'"
        ).fetchone()[0],

        "escalated": conn.execute(
            "SELECT COUNT(*) FROM requests WHERE status = 'escalated'"
        ).fetchone()[0],

        "outreach": conn.execute(
            "SELECT COUNT(*) FROM outreach_log"
        ).fetchone()[0],
    }

    conn.close()

    return data


def get_requests():
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            request_id,
            raw_text,
            blood_type,
            units_needed,
            hospital,
            urgency,
            status,
            created_at
        FROM requests
        ORDER BY
            CASE urgency
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'routine' THEN 3
                ELSE 4
            END,
            request_id DESC
    """).fetchall()

    conn.close()

    return rows


def get_outreach():
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            outreach_id,
            request_id,
            donor_id,
            message_sent,
            sent_at,
            response_status,
            responded_at
        FROM outreach_log
        ORDER BY outreach_id DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return rows


def get_escalations():
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            escalation_id,
            request_id,
            action_taken,
            reason,
            triggered_at
        FROM escalation_log
        ORDER BY escalation_id DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return rows


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DonorLoop",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("DonorLoop")

    st.caption(
        "Blood donation coordination system"
    )

    st.divider()

    st.subheader("View requests")

    selected_urgency = st.selectbox(
        "Priority",
        [
            "All",
            "Critical",
            "High",
            "Routine"
        ]
    )

    selected_status = st.selectbox(
        "Status",
        [
            "All",
            "Open",
            "Resolved",
            "Escalated"
        ]
    )

    st.divider()

    if st.button(
        "Refresh data",
        use_container_width=True
    ):
        st.rerun()

    st.caption(
        "Data source: DonorLoop SQLite database"
    )


# ============================================================
# HEADER
# ============================================================

st.title("Blood Donation Dashboard")

st.caption(
    "Monitor blood requests, donor outreach, and escalation activity."
)

st.divider()


# ============================================================
# SUMMARY
# ============================================================

summary = get_summary()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Registered donors",
        summary["donors"]
    )

with col2:
    st.metric(
        "Blood requests",
        summary["requests"]
    )

with col3:
    st.metric(
        "Open requests",
        summary["open"]
    )

with col4:
    st.metric(
        "Resolved",
        summary["resolved"]
    )


if summary["escalated"] > 0:

    st.info(
        f"{summary['escalated']} request(s) currently require escalation."
    )


# ============================================================
# REQUESTS
# ============================================================

st.divider()

st.subheader("Blood requests")

requests = get_requests()


# Apply filters
filtered_requests = []

for request in requests:

    urgency_match = (
        selected_urgency == "All"
        or request["urgency"].lower()
        == selected_urgency.lower()
    )

    status_match = (
        selected_status == "All"
        or request["status"].lower()
        == selected_status.lower()
    )

    if urgency_match and status_match:
        filtered_requests.append(request)


if not filtered_requests:

    st.info(
        "There are no requests matching the selected filters."
    )

else:

    for request in filtered_requests:

        request_id = request["request_id"]
        blood_type = request["blood_type"]
        units = request["units_needed"]
        hospital = request["hospital"]
        urgency = request["urgency"]
        status = request["status"]

        urgency_text = urgency.capitalize()
        status_text = status.capitalize()

        # Request heading
        st.markdown(
            f"### REQ-{request_id:03d}  ·  {blood_type}"
        )

        # Basic information
        st.write(
            f"**{units} unit(s)** needed at **{hospital}**"
        )

        # Information columns
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.write("Priority")
            st.write(f"**{urgency_text}**")

        with col_b:
            st.write("Status")
            st.write(f"**{status_text}**")

        with col_c:
            st.write("Request ID")
            st.write(f"**REQ-{request_id:03d}**")

        # Original request text
        with st.expander("View request details"):

            st.write(
                request["raw_text"]
            )

            st.caption(
                f"Created: {request['created_at']}"
            )

        st.divider()


# ============================================================
# DONOR OUTREACH
# ============================================================

st.subheader("Recent donor outreach")

outreach = get_outreach()

if not outreach:

    st.info(
        "No donor outreach has been recorded yet."
    )

else:

    for row in outreach:

        request_id = row["request_id"]
        donor_id = row["donor_id"]
        response = row["response_status"]

        if response == "confirmed":
            response_text = "Confirmed"

        elif response == "declined":
            response_text = "Declined"

        elif response == "pending":
            response_text = "Waiting for response"

        elif response == "no_response":
            response_text = "No response"

        else:
            response_text = str(response).replace(
                "_", " "
            ).capitalize()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write(
                f"**REQ-{request_id:03d}**"
            )

        with col2:
            st.write(
                f"Donor #{donor_id}"
            )

        with col3:
            st.write(
                f"**{response_text}**"
            )


# ============================================================
# ESCALATIONS
# ============================================================

st.divider()

st.subheader("Escalation activity")

escalations = get_escalations()

if not escalations:

    st.success(
        "No escalation actions have been recorded."
    )

else:

    for row in escalations:

        request_id = row["request_id"]
        action = row["action_taken"]
        reason = row["reason"]
        triggered_at = row["triggered_at"]

        action_name = action.replace(
            "_", " "
        ).capitalize()

        with st.expander(
            f"REQ-{request_id:03d} · {action_name}"
        ):

            st.write(reason)

            st.caption(
                f"Triggered: {triggered_at}"
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "DonorLoop · Dashboard & Evaluation"
)