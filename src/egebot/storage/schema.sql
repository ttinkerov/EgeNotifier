-- EgeNotifier storage (PostgreSQL)

CREATE TABLE IF NOT EXISTS tg_accounts (
    telegram_id     BIGINT PRIMARY KEY,
    subject_code    SMALLINT NOT NULL,
    session_token   TEXT,
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
CREATE INDEX IF NOT EXISTS idx_accounts_alerts
    ON tg_accounts (alerts_enabled)
    WHERE alerts_enabled AND session_token IS NOT NULL;

CREATE TABLE IF NOT EXISTS score_snapshots (
    telegram_id     BIGINT PRIMARY KEY REFERENCES tg_accounts (telegram_id) ON DELETE CASCADE,
    snapshot_hash   TEXT NOT NULL,
    payload         JSONB NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS score_change_events (
    id              BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT NOT NULL REFERENCES tg_accounts (telegram_id) ON DELETE CASCADE,
    exam_id         INTEGER NOT NULL,
    subject         TEXT NOT NULL,
    old_status      TEXT NOT NULL,
    new_status      TEXT NOT NULL,
    old_mark        SMALLINT,
    new_mark        SMALLINT,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_score_events_user_time
    ON score_change_events (telegram_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS fsm_storage (
    bot_id      BIGINT NOT NULL,
    chat_id     BIGINT NOT NULL,
    user_id     BIGINT NOT NULL,
    destiny     TEXT NOT NULL DEFAULT 'default',
    state       TEXT,
    data        JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (bot_id, chat_id, user_id, destiny)
);
