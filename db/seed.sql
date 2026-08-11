-- ============================================================
-- DonorLoop SQLite Seed Data
-- Synthetic/demo data only
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- OPTIONAL: Clear existing seed data before re-running
-- ============================================================

DELETE FROM escalation_log;
DELETE FROM outreach_log;
DELETE FROM requests;
DELETE FROM donors;

-- ============================================================
-- SYNTHETIC DONOR DATA
-- ============================================================

INSERT INTO donors
(name, blood_type, city, latitude, longitude, phone, last_donation_date)
VALUES

-- Islamabad
('Ali Khan', 'O+', 'Islamabad',
 33.6844, 73.0479, '03001234567', '2026-04-01'),

('Hassan Ahmed', 'A+', 'Islamabad',
 33.7000, 73.0500, '03011234567', '2026-03-15'),

('Usman Tariq', 'B+', 'Islamabad',
 33.6800, 73.0400, '03021234567', '2026-05-20'),

('Hamza Malik', 'O-', 'Islamabad',
 33.6900, 73.0600, '03031234567', '2026-01-10'),

('Bilal Shah', 'AB+', 'Islamabad',
 33.6750, 73.0550, '03041234567', '2026-04-15'),

-- Rawalpindi
('Saad Ahmed', 'A-', 'Rawalpindi',
 33.5651, 73.0169, '03051234567', '2026-02-01'),

('Fahad Ali', 'O+', 'Rawalpindi',
 33.6000, 73.0500, '03061234567', '2026-05-01'),

('Danish Raza', 'B-', 'Rawalpindi',
 33.5800, 73.0300, '03071234567', '2026-03-01'),

('Adeel Khan', 'AB-', 'Rawalpindi',
 33.5900, 73.0200, '03081234567', '2026-01-20'),

-- Lahore
('Ahmed Hassan', 'O-', 'Lahore',
 31.5204, 74.3587, '03091234567', '2026-04-10'),

('Zain Ali', 'A+', 'Lahore',
 31.5000, 74.3400, '03101234567', '2026-05-15'),

('Talha Saeed', 'B+', 'Lahore',
 31.5300, 74.3700, '03111234567', '2026-02-15'),

-- Karachi
('Ahmed Raza', 'O+', 'Karachi',
 24.8607, 67.0011, '03121234567', '2026-04-20'),

('Muneeb Khan', 'A-', 'Karachi',
 24.8700, 67.0100, '03131234567', '2026-03-10'),

('Shahzaib Ali', 'B+', 'Karachi',
 24.8500, 67.0200, '03141234567', '2026-05-05'),

-- Peshawar
('Waleed Khan', 'O+', 'Peshawar',
 34.0151, 71.5249, '03151234567', '2026-04-05'),

('Arham Shah', 'AB+', 'Peshawar',
 34.0200, 71.5300, '03161234567', '2026-02-20'),

-- Multan
('Rayan Ahmed', 'A+', 'Multan',
 30.1575, 71.5249, '03171234567', '2026-05-10'),

('Huzaifa Malik', 'O-', 'Multan',
 30.1600, 71.5300, '03181234567', '2026-03-20'),

-- Intentionally recently donated donor
('Usman Khan', 'O+', 'Islamabad',
 33.6850, 73.0480, '03191234567', '2026-06-20');


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