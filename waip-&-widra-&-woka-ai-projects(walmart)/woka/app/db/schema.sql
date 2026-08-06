-- WOKA Phase 1 schema + supply-chain SQL seeds

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS acl_policies (
    policy_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS acl_rules (
    rule_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id   UUID NOT NULL REFERENCES acl_policies(policy_id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    department  TEXT,
    region      TEXT,
    clearance   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version       INT NOT NULL DEFAULT 1,
    title         TEXT NOT NULL,
    author        TEXT,
    source_key    TEXT NOT NULL,
    parse_status  TEXT NOT NULL DEFAULT 'pending'
                  CHECK (parse_status IN ('pending', 'parsed', 'failed', 'superseded')),
    acl_policy_id UUID REFERENCES acl_policies(policy_id),
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id        UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,
    text          TEXT NOT NULL,
    page_start    INT,
    page_end      INT,
    is_table      BOOLEAN NOT NULL DEFAULT FALSE,
    vector_ref    TEXT,
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (doc_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS ingest_jobs (
    job_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_path   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'running', 'complete', 'failed')),
    docs_total    INT NOT NULL DEFAULT 0,
    docs_done     INT NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       TEXT NOT NULL,
    action        TEXT NOT NULL,
    query_text    TEXT,
    doc_ids       UUID[],
    chunk_ids     UUID[],
    details       JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Supply-chain mock tables (UC-1)
CREATE TABLE IF NOT EXISTS dcs (
    dc_id       TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    region      TEXT NOT NULL,
    city        TEXT,
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION,
    status      TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS stores (
    store_id    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    region      TEXT NOT NULL,
    city        TEXT,
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    region      TEXT,
    risk_tier   TEXT
);

CREATE TABLE IF NOT EXISTS contracts (
    contract_id       TEXT PRIMARY KEY,
    supplier_id       TEXT NOT NULL REFERENCES suppliers(supplier_id),
    allows_alt_source BOOLEAN NOT NULL DEFAULT FALSE,
    notice_hours      INT NOT NULL DEFAULT 48,
    confidentiality   TEXT NOT NULL DEFAULT 'internal',
    effective_date    DATE,
    expiration_date   DATE
);

CREATE TABLE IF NOT EXISTS skus (
    sku         TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    category    TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    id          SERIAL PRIMARY KEY,
    location_id TEXT NOT NULL,
    location_type TEXT NOT NULL CHECK (location_type IN ('dc', 'store')),
    sku         TEXT NOT NULL REFERENCES skus(sku),
    qty         INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    sku         TEXT NOT NULL REFERENCES skus(sku),
    dest_dc     TEXT NOT NULL REFERENCES dcs(dc_id),
    status      TEXT NOT NULL,
    eta_hours   INT
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(parse_status);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory(sku);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);

-- ACL seeds
INSERT INTO acl_policies (name, description) VALUES
    ('general_employee', 'Store / DC associates'),
    ('supply_chain_ops', 'Supply chain operations'),
    ('finance_analyst', 'Finance analysts'),
    ('executive', 'Executive leadership')
ON CONFLICT (name) DO NOTHING;

INSERT INTO acl_rules (policy_id, role, department, region, clearance)
SELECT p.policy_id, v.role, v.department, v.region, v.clearance
FROM acl_policies p
JOIN (VALUES
    ('general_employee', 'associate', 'Store Ops', 'US', 'internal'),
    ('supply_chain_ops', 'analyst', 'Supply Chain', 'US', 'internal'),
    ('finance_analyst', 'analyst', 'Finance', 'US', 'confidential'),
    ('executive', 'executive', '*', 'US', 'restricted')
) AS v(policy_name, role, department, region, clearance) ON p.name = v.policy_name
WHERE NOT EXISTS (
    SELECT 1 FROM acl_rules r WHERE r.policy_id = p.policy_id AND r.role = v.role
);

-- UC-1 seeds
INSERT INTO dcs (dc_id, name, region, city, lat, lon, status) VALUES
    ('ATL-01', 'Atlanta DC', 'SE', 'Atlanta', 33.75, -84.39, 'closed'),
    ('JAX-02', 'Jacksonville DC', 'SE', 'Jacksonville', 30.33, -81.66, 'closed'),
    ('MEM-03', 'Memphis DC', 'SE', 'Memphis', 35.15, -90.05, 'open'),
    ('DAL-04', 'Dallas DC', 'SC', 'Dallas', 32.78, -96.80, 'open')
ON CONFLICT (dc_id) DO UPDATE SET status = EXCLUDED.status;

INSERT INTO stores (store_id, name, region, city, lat, lon) VALUES
    ('S-1001', 'Atlanta Metro #1001', 'SE', 'Atlanta', 33.77, -84.40),
    ('S-1044', 'Savannah #1044', 'SE', 'Savannah', 32.08, -81.09),
    ('S-2100', 'Nashville #2100', 'SE', 'Nashville', 36.16, -86.78)
ON CONFLICT (store_id) DO NOTHING;

INSERT INTO suppliers (supplier_id, name, region, risk_tier) VALUES
    ('SUP-ACME', 'Acme Logistics', 'SE', 'high'),
    ('SUP-GULF', 'GulfFresh Produce', 'SE', 'high'),
    ('SUP-NORTH', 'Northern Goods Co', 'MW', 'low')
ON CONFLICT (supplier_id) DO NOTHING;

INSERT INTO contracts (contract_id, supplier_id, allows_alt_source, notice_hours, confidentiality, effective_date, expiration_date) VALUES
    ('C-ACME-2024', 'SUP-ACME', TRUE, 48, 'internal', '2024-01-01', '2026-12-31'),
    ('C-GULF-2023', 'SUP-GULF', TRUE, 48, 'internal', '2023-06-01', '2026-06-01'),
    ('C-NORTH-2025', 'SUP-NORTH', FALSE, 72, 'confidential', '2025-01-01', '2027-01-01')
ON CONFLICT (contract_id) DO NOTHING;

INSERT INTO skus (sku, description, category) VALUES
    ('TV-55-4K', '55-inch 4K Television', 'Electronics'),
    ('MILK-GAL', 'Gallon Whole Milk', 'Grocery'),
    ('WATER-24', 'Bottled Water 24pk', 'Grocery')
ON CONFLICT (sku) DO NOTHING;

DELETE FROM inventory;
INSERT INTO inventory (location_id, location_type, sku, qty) VALUES
    ('MEM-03', 'dc', 'TV-55-4K', 12400),
    ('MEM-03', 'dc', 'MILK-GAL', 8200),
    ('MEM-03', 'dc', 'WATER-24', 15000),
    ('DAL-04', 'dc', 'TV-55-4K', 5000),
    ('S-1001', 'store', 'MILK-GAL', 40),
    ('S-1044', 'store', 'MILK-GAL', 25),
    ('S-2100', 'store', 'MILK-GAL', 180),
    ('S-1001', 'store', 'TV-55-4K', 12);

DELETE FROM shipments;
INSERT INTO shipments (shipment_id, supplier_id, sku, dest_dc, status, eta_hours) VALUES
    ('SH-9001', 'SUP-ACME', 'TV-55-4K', 'ATL-01', 'delayed', 72),
    ('SH-9002', 'SUP-GULF', 'MILK-GAL', 'JAX-02', 'delayed', 36),
    ('SH-9003', 'SUP-NORTH', 'WATER-24', 'MEM-03', 'in_transit', 12);
