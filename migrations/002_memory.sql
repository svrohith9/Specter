CREATE TABLE IF NOT EXISTS summaries (
    id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    source_count INT DEFAULT 0,
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_summaries_created ON summaries(created_at);
