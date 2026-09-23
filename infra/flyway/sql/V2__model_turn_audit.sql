CREATE TABLE model_turns (
    id BIGSERIAL PRIMARY KEY,
    investigation_id BIGINT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    direction VARCHAR(32) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_turns_investigation_id ON model_turns (investigation_id, turn_number);
