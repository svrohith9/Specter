CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    attributes JSON,
    vector BLOB,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    access_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES entities(id),
    target_id TEXT REFERENCES entities(id),
    relation_type TEXT NOT NULL,
    strength FLOAT,
    context JSON,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    intent TEXT NOT NULL,
    graph_json JSON NOT NULL,
    status TEXT,
    result JSON,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INT
);

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    signature JSON NOT NULL,
    code TEXT NOT NULL,
    tests TEXT,
    version INT DEFAULT 1,
    performance JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT,
    action TEXT,
    details JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entities_type_name ON entities(type, name);
CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
