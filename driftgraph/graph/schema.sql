-- DriftGraph SQLite Schema with Full-Text Search (FTS5)

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT,
    source_file TEXT,
    source_type TEXT DEFAULT 'markdown',
    date TEXT,
    tags TEXT,
    raw_content TEXT,
    deleted_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notes_deleted_at ON notes(deleted_at);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    note_id TEXT,
    source_file TEXT,
    chunk_index INTEGER,
    text TEXT,
    start_char INTEGER,
    end_char INTEGER,
    token_count INTEGER,
    FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    degree INTEGER DEFAULT 0,
    community_id INTEGER,
    community_levels TEXT,
    embedding_blob BLOB,
    provenance TEXT,
    layout_x REAL,
    layout_y REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    predicate TEXT NOT NULL,
    description TEXT,
    weight REAL DEFAULT 1.0,
    confidence REAL DEFAULT 1.0,
    provenance TEXT,
    FOREIGN KEY(source) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY(target) REFERENCES nodes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS communities (
    id INTEGER PRIMARY KEY,
    level INTEGER NOT NULL,
    parent_id INTEGER,
    name TEXT NOT NULL,
    node_ids TEXT,
    summary TEXT,
    findings TEXT,
    themes TEXT,
    confidence REAL DEFAULT 1.0
);

-- Full-Text Search Table for Chunks
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    note_id UNINDEXED,
    text,
    title,
    tokenize = 'porter unicode61'
);

-- Full-Text Search Table for Community Summaries
CREATE VIRTUAL TABLE IF NOT EXISTS communities_fts USING fts5(
    community_id UNINDEXED,
    level UNINDEXED,
    name,
    summary,
    themes,
    tokenize = 'porter unicode61'
);

-- Key/Value metadata (global summaries, build timestamps, etc.)
CREATE TABLE IF NOT EXISTS graph_meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
