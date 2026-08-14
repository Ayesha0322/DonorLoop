-- ============================================================
-- DonorLoop SQLite Seed Data
-- Synthetic/demo data only
-- ============================================================
--
-- NOTE: Donor data is no longer seeded here. Donors come from
-- data/synthetic_donors.csv via `python data/load_donors.py`
-- (200 Faker-generated donors, one source of truth instead of
-- duplicating a hand-written donor list here).
--
-- RUN ORDER for a fresh demo database:
--   1.python -c "import sqlite3, pathlib; pathlib.Path('db').mkdir(exist_ok=True); conn = sqlite3.connect('db/donorloop.db'); conn.executescript(open('schema.sql').read()); conn.close(); print('schema applied')"
--   2.python data/load_donors.py
--   3.python -c "import sqlite3; conn = sqlite3.connect('db/donorloop.db'); conn.executescript(open('seed.sql').read()); conn.close(); print('seed applied')"

PRAGMA foreign_keys = ON;

-- ============================================================
-- OPTIONAL: Clear existing seed data before re-running
-- (donors is intentionally NOT cleared here - that's load_donors.py's job)
-- ============================================================

DELETE FROM escalation_log;
DELETE FROM outreach_log;
DELETE FROM requests;

-- ============================================================
-- SAMPLE BLOOD REQUESTS
-- ============================================================

INSERT INTO requests
(
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
VALUES

(
    'Urgent! We need 2 units of O+ blood at Shifa Hospital Islamabad for a patient undergoing surgery immediately.',
    'O+',
    2,
    'Shifa Hospital',
    33.6844,
    73.0479,
    'critical',
    'open',
    '2026-08-11T09:00:00'
),

(
    'A+ blood required at Shifa Hospital Islamabad. One unit is needed today.',
    'A+',
    1,
    'Shifa Hospital',
    33.6844,
    73.0479,
    'high',
    'open',
    '2026-08-11T09:05:00'
),

(
    'We need 3 units of B+ blood at Holy Family Hospital Rawalpindi for a scheduled operation tomorrow.',
    'B+',
    3,
    'Holy Family Hospital',
    33.5651,
    73.0169,
    'high',
    'open',
    '2026-08-11T09:10:00'
),

(
    'Routine requirement: one unit of O- blood needed at Mayo Hospital Lahore for a planned procedure next week.',
    'O-',
    1,
    'Mayo Hospital',
    31.5204,
    74.3587,
    'routine',
    'open',
    '2026-08-11T09:15:00'
),

(
    'Emergency! AB+ blood needed immediately at Lady Reading Hospital Peshawar.',
    'AB+',
    2,
    'Lady Reading Hospital',
    34.0151,
    71.5249,
    'critical',
    'escalated',
    '2026-08-11T09:20:00'
);

-- ============================================================
-- SAMPLE OUTREACH LOG
-- ============================================================
-- NOTE: donor_id values below (1, 2, 3, 4, 10) simply reference
-- whichever donors end up at those row positions after
-- load_donors.py runs - real names/blood types will differ from
-- the original hand-written version, but the IDs will still exist
-- since the CSV loads 200 rows. This is fine for demoing the
-- outreach_log/escalation_log mechanics; it's not meant to be a
-- perfectly consistent narrative against the current donor names.

INSERT INTO outreach_log
(
    request_id,
    donor_id,
    message_sent,
    sent_at,
    response_status,
    responded_at
)
VALUES

(
    1,
    1,
    'DonorLoop: An urgent O+ blood request has been received at Shifa Hospital Islamabad. You appear to be a compatible nearby donor. Are you available to donate 2 units?',
    '2026-08-11T09:01:00',
    'confirmed',
    '2026-08-11T09:05:00'
),

(
    1,
    4,
    'DonorLoop: An urgent O+ blood request has been received at Shifa Hospital Islamabad. Are you available to donate?',
    '2026-08-11T09:02:00',
    'pending',
    NULL
),

(
    2,
    2,
    'DonorLoop: A+ blood is required today at Shifa Hospital Islamabad. Are you available to donate one unit?',
    '2026-08-11T09:06:00',
    'confirmed',
    '2026-08-11T09:09:00'
),

(
    3,
    3,
    'DonorLoop: B+ blood is required at Holy Family Hospital Rawalpindi for an upcoming operation. Are you available?',
    '2026-08-11T09:11:00',
    'declined',
    '2026-08-11T09:15:00'
),

(
    4,
    10,
    'DonorLoop: O- blood is required at Mayo Hospital Lahore for a planned procedure. Are you available to donate?',
    '2026-08-11T09:16:00',
    'pending',
    NULL
);

-- ============================================================
-- SAMPLE ESCALATION LOG
-- ============================================================

INSERT INTO escalation_log
(
    request_id,
    action_taken,
    reason,
    triggered_at
)
VALUES
(
    5,
    'widen_radius',
    'No sufficient compatible donors responded within the escalation window.',
    '2026-08-11T09:30:00'
);

-- ============================================================
-- VERIFY SEEDED DATA
-- ============================================================

SELECT 'donors' AS table_name, COUNT(*) AS row_count
FROM donors

UNION ALL

SELECT 'requests', COUNT(*)
FROM requests

UNION ALL

SELECT 'outreach_log', COUNT(*)
FROM outreach_log

UNION ALL

SELECT 'escalation_log', COUNT(*)
FROM escalation_log;
