"""
dashboard/pages/1_Live_Request.py

Live demo page: submit a real free-text blood request, watch it flow
through NLP extraction -> the agent's donor matching -> outreach ->
escalation, with a map that visually shows the search radius expanding
if not enough donors respond right away.

Streamlit auto-detects anything in a `pages/` folder next to the main
app.py and adds it as an extra sidebar page - this file doesn't touch
app.py at all.
"""

import sys
import time
from pathlib import Path

import pydeck as pdk
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

import config
from nlp.extract import process_request
from agent.orchestrator import run_agent_loop_steps


st.set_page_config(page_title="DonorLoop - Live Request", page_icon="🩸", layout="wide")

st.title("Submit a Live Blood Request")
st.caption(
    "Type a request the way a hospital or family member actually would. "
    "Watch NLP extraction, donor matching, outreach, and autonomous "
    "escalation happen in real time."
)

st.divider()

example = (
    "Urgent! We need 2 units of AB+ blood at Lady Reading Hospital "
    "Peshawar immediately."
)

text = st.text_area(
    "Request text",
    value=example,
    height=100,
    help="Free text, the same way a WhatsApp/social-media appeal would be written.",
)

top_n = st.slider("Donors to contact per round", min_value=1, max_value=10, value=5)

submit = st.button("Submit request", type="primary")


def draw_map(hospital_lat, hospital_lon, radius_km, contacted, placeholder):
    """Renders hospital + contacted donors + a circle showing current search radius."""

    radius_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": hospital_lat, "lon": hospital_lon}],
        get_position="[lon, lat]",
        get_radius=radius_km * 1000,   # meters
        get_fill_color=[220, 30, 30, 40],
        stroked=True,
        get_line_color=[220, 30, 30, 160],
        line_width_min_pixels=2,
    )

    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": hospital_lat, "lon": hospital_lon}],
        get_position="[lon, lat]",
        get_radius=400,
        get_fill_color=[0, 0, 0, 255],
    )

    donor_data = [
        {"lat": d["latitude"], "lon": d["longitude"], "name": d["name"],
         "blood_type": d["blood_type"], "distance": d["distance_km"]}
        for d in contacted
    ]
    donor_layer = pdk.Layer(
        "ScatterplotLayer",
        data=donor_data,
        get_position="[lon, lat]",
        get_radius=300,
        get_fill_color=[30, 100, 220, 220],
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=hospital_lat, longitude=hospital_lon,
        zoom=10, pitch=0,
    )

    deck = pdk.Deck(
        layers=[radius_layer, donor_layer, hospital_layer],
        initial_view_state=view_state,
        tooltip={"text": "{name} ({blood_type}) - {distance} km"},
        map_style=None,
    )

    placeholder.pydeck_chart(deck)


if submit:
    if not text.strip():
        st.error("Enter a request first.")
        st.stop()

    with st.spinner("Running NLP extraction..."):
        extracted = process_request(text)

    missing = [f for f in ["blood_type", "units_needed", "hospital",
                            "hospital_latitude", "hospital_longitude"]
               if extracted.get(f) is None]
    if missing:
        st.error(f"Could not extract: {', '.join(missing)}. Try rephrasing the request "
                  f"(make sure it names a known city and includes a unit count).")
        st.stop()

    st.success(
        f"Extracted: **{extracted['blood_type']}**, "
        f"**{extracted['units_needed']} unit(s)**, "
        f"**{extracted['hospital']}**, "
        f"urgency: **{extracted['urgency']}**"
    )

    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO requests
           (raw_text, blood_type, units_needed, hospital, hospital_latitude,
            hospital_longitude, urgency, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'open', datetime('now'))""",
        (extracted["raw_text"], extracted["blood_type"], extracted["units_needed"],
         extracted["hospital"], extracted["hospital_latitude"],
         extracted["hospital_longitude"], extracted["urgency"]),
    )
    request_id = cur.lastrowid
    conn.commit()
    conn.close()

    st.divider()
    st.subheader(f"Live agent activity - REQ-{request_id:03d}")

    status_box = st.empty()
    map_placeholder = st.empty()

    for state in run_agent_loop_steps(request_id, simulate=True, top_n=top_n):
        req = state["request"]

        with status_box.container():
            c1, c2, c3 = st.columns(3)
            c1.metric("Search radius", f"{state['radius_km']} km")
            c2.metric("Donors contacted this round", len(state["contacted"]))
            c3.metric("Confirmed", f"{state['confirmed']} / {state['units_needed']}")

            if state["status"] == "escalating":
                st.warning(f"**Escalating: {state['action']}** - {state['reason']}")
            elif state["status"] == "resolved":
                st.success(f"Request resolved - {state['confirmed']}/{state['units_needed']} donors confirmed.")
            elif state["status"] == "escalated":
                st.error(f"Escalated to human coordinator - {state['reason']}")

        draw_map(
            req["hospital_latitude"], req["hospital_longitude"],
            state["radius_km"], state["contacted"], map_placeholder,
        )

        if state["status"] in ("resolved", "escalated"):
            break

        time.sleep(1.5)  # pause so the radius change is visible, not instant
