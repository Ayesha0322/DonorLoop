-- DonorLoop shared database schema
-- Run once to create db/donorloop.db
-- Every module reads/writes to THESE table and column names — do not rename locally.

-- Module A owns this table (donor pool)
CREATE TABLE IF NOT EXISTS donors (
    donor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    blood_type TEXT NOT NULL,          -- e.g. 'O-', 'A+', 'AB-'
    city TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    phone TEXT NOT NULL,               -- fake/synthetic for MVP
    last_donation_date TEXT NOT NULL   -- ISO format: 'YYYY-MM-DD'
);

-- Module B writes here after extracting a request; Module C reads it
CREATE TABLE IF NOT EXISTS requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_text TEXT,                     -- original free-text request, if any
    blood_type TEXT NOT NULL,
    units_needed INTEGER NOT NULL,
    hospital TEXT NOT NULL,
    hospital_latitude REAL NOT NULL,
    hospital_longitude REAL NOT NULL,
    urgency TEXT NOT NULL,             -- 'critical' | 'high' | 'routine'
    status TEXT NOT NULL DEFAULT 'open',  -- 'open' | 'escalated' | 'resolved' | 'closed'
    created_at TEXT NOT NULL           -- ISO datetime
);

-- Module C writes here every time it contacts a donor
CREATE TABLE IF NOT EXISTS outreach_log (
    outreach_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL REFERENCES requests(request_id),
    donor_id INTEGER NOT NULL REFERENCES donors(donor_id),
    message_sent TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    response_status TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'confirmed' | 'declined' | 'no_response'
    responded_at TEXT
);

-- Module C writes here every time the agent escalates
CREATE TABLE IF NOT EXISTS escalation_log (
    escalation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL REFERENCES requests(request_id),
    action_taken TEXT NOT NULL,        -- 'widen_radius' | 'relax_compatibility' | 'notify_blood_bank'
    reason TEXT NOT NULL,              -- human-readable explanation, shown on dashboard
    triggered_at TEXT NOT NULL
);
