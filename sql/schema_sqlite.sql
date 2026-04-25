-- SQLite schema for part 2: database + image search backend
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    original_path TEXT,
    stored_path TEXT NOT NULL,
    original_width INTEGER,
    original_height INTEGER,
    original_aspect REAL,
    channels INTEGER,
    status TEXT DEFAULT 'success',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feature_vectors (
    image_id INTEGER PRIMARY KEY,
    vector_dim INTEGER NOT NULL,
    raw_vector BLOB NOT NULL,
    norm_vector BLOB NOT NULL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vector_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_images_filename ON images(filename);
CREATE INDEX IF NOT EXISTS idx_images_status ON images(status);
