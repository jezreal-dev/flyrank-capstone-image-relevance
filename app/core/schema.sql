-- ==============================================================================
-- AI Image Understanding & Content Matching Engine: SQLite Schema
-- Includes robust indexes, foreign keys, and audit logging
-- ==============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued', 'processing', 'completed', 'flagged_for_review', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS image_metadata (
    image_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    category TEXT NOT NULL,
    attributes_json TEXT NOT NULL,
    caption TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    is_flagged INTEGER NOT NULL DEFAULT 0 CHECK(is_flagged IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK(entity_type IN ('image', 'post')),
    entity_id TEXT NOT NULL,
    vector_json TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    target_subject TEXT,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suggestions (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    image_id TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    guard_decision TEXT NOT NULL CHECK(guard_decision IN ('ACCEPTED', 'REJECTED_CATEGORY_MISMATCH', 'REJECTED_LOW_CONFIDENCE', 'REJECTED_LOW_SIMILARITY')),
    explanation TEXT NOT NULL,
    rank INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS review_decisions (
    id TEXT PRIMARY KEY,
    suggestion_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('APPROVED', 'REJECTED')),
    reviewer_notes TEXT,
    decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (suggestion_id) REFERENCES suggestions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cost_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    model_name TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS batch_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'completed', 'failed')),
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    flagged_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- ==============================================================================
-- Production Indexes
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_images_status ON images(status);
CREATE INDEX IF NOT EXISTS idx_image_meta_category ON image_metadata(category);
CREATE INDEX IF NOT EXISTS idx_image_meta_confidence ON image_metadata(confidence);
CREATE INDEX IF NOT EXISTS idx_image_meta_flagged ON image_metadata(is_flagged);
CREATE INDEX IF NOT EXISTS idx_embeddings_lookup ON embeddings(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_post_rank ON suggestions(post_id, rank);
CREATE INDEX IF NOT EXISTS idx_review_suggestion ON review_decisions(suggestion_id);
CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status);
