CREATE TABLE incidents (
    id BIGSERIAL PRIMARY KEY,
    alert_fingerprint VARCHAR(255) UNIQUE,
    service VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE TABLE investigations (
    id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT NOT NULL REFERENCES incidents(id),
    root_cause TEXT NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evidence (
    id BIGSERIAL PRIMARY KEY,
    investigation_id BIGINT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    finding TEXT NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tool_calls (
    id BIGSERIAL PRIMARY KEY,
    investigation_id BIGINT REFERENCES investigations(id) ON DELETE CASCADE,
    event VARCHAR(64) NOT NULL,
    tool_name VARCHAR(255),
    arguments JSONB,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recommendations (
    id BIGSERIAL PRIMARY KEY,
    investigation_id BIGINT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    requires_approval BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE approval_requests (
    id BIGSERIAL PRIMARY KEY,
    investigation_id BIGINT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMPTZ
);

CREATE INDEX idx_investigations_incident_id ON investigations (incident_id);
CREATE INDEX idx_evidence_investigation_id ON evidence (investigation_id);
CREATE INDEX idx_tool_calls_investigation_id ON tool_calls (investigation_id);
CREATE INDEX idx_recommendations_investigation_id ON recommendations (investigation_id);
