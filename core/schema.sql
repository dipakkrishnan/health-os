PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS connections (
    connection_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    fhir_base TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    token_endpoint TEXT,
    dynamic_client_id TEXT,
    credential_ref TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_runs (
    sync_run_id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL REFERENCES connections(connection_id),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'complete', 'partial', 'failed')),
    error TEXT
);

CREATE TABLE IF NOT EXISTS raw_blobs (
    sha256 TEXT PRIMARY KEY,
    relative_path TEXT NOT NULL UNIQUE,
    media_type TEXT NOT NULL,
    byte_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_pages (
    sync_run_id TEXT NOT NULL REFERENCES sync_runs(sync_run_id),
    dataset TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    request_url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    blob_sha256 TEXT NOT NULL REFERENCES raw_blobs(sha256),
    PRIMARY KEY (sync_run_id, dataset, page_number)
);

CREATE TABLE IF NOT EXISTS resources (
    resource_version_key TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL REFERENCES connections(connection_id),
    logical_key TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    version_id TEXT,
    content_sha256 TEXT NOT NULL,
    source_blob_sha256 TEXT NOT NULL REFERENCES raw_blobs(sha256),
    json_pointer TEXT NOT NULL,
    content_json TEXT NOT NULL,
    first_seen_run_id TEXT NOT NULL REFERENCES sync_runs(sync_run_id),
    last_seen_run_id TEXT NOT NULL REFERENCES sync_runs(sync_run_id),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    UNIQUE (connection_id, logical_key, content_sha256)
);

CREATE INDEX IF NOT EXISTS resources_logical_key_idx
    ON resources(connection_id, logical_key);

CREATE TABLE IF NOT EXISTS clinical_items (
    clinical_item_id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL REFERENCES connections(connection_id),
    resource_version_key TEXT NOT NULL REFERENCES resources(resource_version_key),
    logical_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    effective_start TEXT,
    effective_end TEXT,
    recorded_at TEXT,
    status TEXT,
    code_system TEXT,
    code TEXT,
    display TEXT NOT NULL,
    value_json TEXT NOT NULL,
    assertion_origin TEXT NOT NULL,
    source_blob_sha256 TEXT NOT NULL REFERENCES raw_blobs(sha256),
    evidence_json TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (resource_version_key, kind, parser_version)
);

CREATE INDEX IF NOT EXISTS clinical_items_time_idx
    ON clinical_items(effective_start, recorded_at);

CREATE INDEX IF NOT EXISTS clinical_items_kind_idx
    ON clinical_items(kind, code);

CREATE TABLE IF NOT EXISTS coverage (
    connection_id TEXT NOT NULL REFERENCES connections(connection_id),
    dataset TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'empty', 'error')),
    item_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT NOT NULL,
    last_success_at TEXT,
    error TEXT,
    PRIMARY KEY (connection_id, dataset)
);
