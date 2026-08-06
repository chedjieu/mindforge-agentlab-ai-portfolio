-- WIDRA Phase 1 schema

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

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(parse_status);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id, created_at DESC);

-- Seed default ACL policies
INSERT INTO acl_policies (name, description)
VALUES
    ('general_employee', 'All US store associates'),
    ('finance_analyst', 'Finance department analysts'),
    ('compliance_officer', 'Compliance and legal team'),
    ('executive', 'Executive leadership — restricted')
ON CONFLICT (name) DO NOTHING;

INSERT INTO acl_rules (policy_id, role, department, region)
SELECT p.policy_id, v.role, v.department, v.region
FROM acl_policies p
JOIN (VALUES
    ('general_employee', 'associate', 'Store Ops', 'US'),
    ('finance_analyst', 'analyst', 'Finance', 'US'),
    ('compliance_officer', 'officer', 'Compliance', 'US'),
    ('executive', 'executive', '*', 'US')
) AS v(policy_name, role, department, region) ON p.name = v.policy_name
WHERE NOT EXISTS (
    SELECT 1 FROM acl_rules r WHERE r.policy_id = p.policy_id AND r.role = v.role
);
