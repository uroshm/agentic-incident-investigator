CREATE TABLE investigation_agents (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_versions (
    id BIGSERIAL PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES investigation_agents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    instructions TEXT NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(255) NOT NULL DEFAULT 'local-user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ,
    UNIQUE (agent_id, version)
);

CREATE TABLE tool_definitions (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    kind VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    definition JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_tool_bindings (
    agent_version_id BIGINT NOT NULL REFERENCES agent_versions(id) ON DELETE CASCADE,
    tool_definition_id BIGINT NOT NULL REFERENCES tool_definitions(id),
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (agent_version_id, tool_definition_id)
);

CREATE TABLE registry_audit_events (
    id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(64) NOT NULL,
    entity_id BIGINT,
    action VARCHAR(64) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor VARCHAR(255) NOT NULL DEFAULT 'local-user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_versions_agent_id ON agent_versions (agent_id);
CREATE INDEX idx_agent_tool_bindings_version_id ON agent_tool_bindings (agent_version_id);
CREATE INDEX idx_registry_audit_entity ON registry_audit_events (entity_type, entity_id);
