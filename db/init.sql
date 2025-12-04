CREATE TABLE IF NOT EXISTS flats (
    flat_id SERIAL PRIMARY KEY,
    flat_no VARCHAR(10) NOT NULL UNIQUE,
    owner_name VARCHAR(100),
    phone_number VARCHAR(20),
    whatsapp_number VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS maintenance_payments (
    id SERIAL PRIMARY KEY,
    flat_id INT NOT NULL REFERENCES flats(flat_id),
    month_year VARCHAR(7) NOT NULL, -- '2025-12'
    is_paid BOOLEAN NOT NULL DEFAULT FALSE,
    paid_on TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    flat_id INT NOT NULL REFERENCES flats(flat_id),
    month_year VARCHAR(7) NOT NULL,
    details_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Sample flats
INSERT INTO flats (flat_no, owner_name, phone_number, whatsapp_number)
VALUES
  ('C-101', 'Test Owner 1', '+910000000001', '+910000000001'),
  ('B-302', 'Test Owner 2', '+910000000002', '+910000000002')
ON CONFLICT (flat_no) DO NOTHING;

-- B-302 has paid Dec 2025
INSERT INTO maintenance_payments (flat_id, month_year, is_paid, paid_on)
SELECT flat_id, '2025-12', TRUE, NOW()
FROM flats WHERE flat_no = 'B-302'
ON CONFLICT DO NOTHING;

-- C-101 has NOT paid Dec 2025
INSERT INTO maintenance_payments (flat_id, month_year, is_paid, paid_on)
SELECT flat_id, '2025-12', FALSE, NULL
FROM flats WHERE flat_no = 'C-101'
ON CONFLICT DO NOTHING;
