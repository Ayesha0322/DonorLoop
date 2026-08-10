"""
DonorLoop shared configuration.
Everyone imports FROM this file instead of hardcoding paths/values in their own module.
Secrets (API keys) go in a local .env file (never committed to git) and are loaded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env in the repo root, if present

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "donorloop.db"
SYNTHETIC_DONORS_CSV = BASE_DIR / "data" / "synthetic_donors.csv"
SAMPLE_REQUESTS_JSON = BASE_DIR / "demo" / "sample_requests.json"

# --- API keys (set these in your local .env file, never hardcode) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

# --- Business rules (Module A owns the values, everyone reads from here) ---
ELIGIBILITY_WINDOW_DAYS = 90          # min days since last donation
DEFAULT_SEARCH_RADIUS_KM = 15         # initial donor search radius
ESCALATED_SEARCH_RADIUS_KM = 40       # radius after first escalation

# --- Agent behavior (Module C owns the values) ---
RESPONSE_WINDOW_MINUTES = 10          # how long to wait for donor responses before escalating (demo-scale)
MIN_CONFIRMATIONS_NEEDED_DEFAULT = 1  # can be overridden per-request via units_needed

# --- Blood type compatibility matrix (Module A owns this — fixed medical rule, not learned) ---
COMPATIBILITY = {
    "O-":  ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],  # universal donor
    "O+":  ["O+", "A+", "B+", "AB+"],
    "A-":  ["A-", "A+", "AB-", "AB+"],
    "A+":  ["A+", "AB+"],
    "B-":  ["B-", "B+", "AB-", "AB+"],
    "B+":  ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}

# --- Example .env file content (save this as .env in the repo root, DO NOT commit it) ---
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
# TWILIO_ACCOUNT_SID=ACxxxxxxxx
# TWILIO_AUTH_TOKEN=xxxxxxxx
