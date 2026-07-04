-- EgeNotifier storage (PostgreSQL)

CREATE TABLE IF NOT EXISTS tg_accounts (
    telegram_id     BIGINT PRIMARY KEY,
    subject_code    SMALLINT NOT NULL,
    session_token   TEXT NOT NULL,
    alerts_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
    spoiler_scores  BOOLEAN NOT NULL DEFAULT FALSE,
    linked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    snapshot_hash   TEXT
);

CREATE TABLE IF NOT EXISTS auth_drafts (
    telegram_id     BIGINT PRIMARY KEY,
    step            TEXT NOT NULL,
    name_digest     TEXT,
    subject_code    SMALLINT,
    document_ref    TEXT,
    challenge_id    TEXT,
    challenge_reply TEXT
);

CREATE INDEX IF NOT EXISTS idx_accounts_subject ON tg_accounts (subject_code);
CREATE INDEX IF NOT EXISTS idx_accounts_alerts ON tg_accounts (alerts_enabled) WHERE alerts_enabled;
