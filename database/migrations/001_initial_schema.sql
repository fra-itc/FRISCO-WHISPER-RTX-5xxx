-- ============================================================================
-- FRISCO WHISPER RTX 5xxx - Initial Database Schema
-- Migration: 001_initial_schema.sql
-- Created: 2025-11-20
-- Description: Initial database schema for transcription job management
-- ============================================================================

-- Enable foreign key support
PRAGMA foreign_keys = ON;

-- ============================================================================
-- TABLE: files
-- Purpose: Store unique file information with deduplication via hash
-- ============================================================================
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT NOT NULL UNIQUE,           -- SHA256 hash for duplicate detection
    original_name TEXT NOT NULL,              -- Original filename
    file_path TEXT NOT NULL,                  -- Current file path
    size_bytes INTEGER NOT NULL,              -- File size in bytes
    format TEXT NOT NULL,                     -- Audio format (m4a, mp3, wav, etc.)
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for performance
    CONSTRAINT chk_size_positive CHECK (size_bytes > 0),
    CONSTRAINT chk_format_valid CHECK (format IN ('m4a', 'mp3', 'wav', 'mp4', 'aac', 'flac', 'opus', 'waptt.opus'))
);

-- Index for file hash lookups (duplicate detection)
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash);

-- Index for filename searches
CREATE INDEX IF NOT EXISTS idx_files_name ON files(original_name);

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_files_uploaded ON files(uploaded_at DESC);

-- ============================================================================
-- TABLE: transcription_jobs
-- Purpose: Track transcription job lifecycle and metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS transcription_jobs (
    job_id TEXT PRIMARY KEY,                  -- UUID for job tracking
    file_id INTEGER NOT NULL,                 -- Foreign key to files table
    file_name TEXT NOT NULL,                  -- Cached filename for convenience
    model_size TEXT NOT NULL,                 -- Whisper model (tiny, base, small, medium, large-v3)
    status TEXT NOT NULL DEFAULT 'pending',   -- pending, processing, completed, failed
    task_type TEXT NOT NULL DEFAULT 'transcribe', -- transcribe or translate
    language TEXT,                            -- Source language (NULL for auto-detect)
    detected_language TEXT,                   -- Auto-detected language
    language_probability REAL,                -- Confidence of language detection
    compute_type TEXT,                        -- float16, int8, float32
    device TEXT,                              -- cuda or cpu
    beam_size INTEGER DEFAULT 5,              -- Beam search size
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,                     -- When processing started
    completed_at TIMESTAMP,                   -- When processing completed
    duration_seconds REAL,                    -- Audio duration in seconds
    processing_time_seconds REAL,             -- Time taken to process
    error_message TEXT,                       -- Error details if failed

    -- Foreign key constraint
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT chk_status_valid CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    CONSTRAINT chk_task_type_valid CHECK (task_type IN ('transcribe', 'translate')),
    CONSTRAINT chk_model_valid CHECK (model_size IN ('tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3')),
    CONSTRAINT chk_compute_valid CHECK (compute_type IS NULL OR compute_type IN ('float16', 'float32', 'int8', 'int8_float32')),
    CONSTRAINT chk_device_valid CHECK (device IS NULL OR device IN ('cuda', 'cpu')),
    CONSTRAINT chk_duration_positive CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    CONSTRAINT chk_processing_time_positive CHECK (processing_time_seconds IS NULL OR processing_time_seconds >= 0)
);

-- Index for job status queries
CREATE INDEX IF NOT EXISTS idx_jobs_status ON transcription_jobs(status);

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_jobs_created ON transcription_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_updated ON transcription_jobs(updated_at DESC);

-- Index for file_id lookups
CREATE INDEX IF NOT EXISTS idx_jobs_file_id ON transcription_jobs(file_id);

-- Composite index for common queries (status + created_at)
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON transcription_jobs(status, created_at DESC);

-- ============================================================================
-- TABLE: transcriptions
-- Purpose: Store transcription results and metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,                     -- Foreign key to transcription_jobs
    text TEXT NOT NULL,                       -- Full transcription text
    language TEXT NOT NULL,                   -- Language of transcription
    segment_count INTEGER NOT NULL DEFAULT 0, -- Number of segments
    segments TEXT NOT NULL,                   -- JSON array of segments with timestamps
    srt_path TEXT,                           -- Path to generated SRT file
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    FOREIGN KEY (job_id) REFERENCES transcription_jobs(job_id) ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT chk_segment_count_positive CHECK (segment_count >= 0)
);

-- Index for job_id lookups
CREATE INDEX IF NOT EXISTS idx_transcriptions_job ON transcriptions(job_id);

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_transcriptions_created ON transcriptions(created_at DESC);

-- Index for language queries
CREATE INDEX IF NOT EXISTS idx_transcriptions_language ON transcriptions(language);

-- ============================================================================
-- FULL-TEXT SEARCH: transcriptions_fts
-- Purpose: Enable fast full-text search on transcription content
-- ============================================================================
CREATE VIRTUAL TABLE IF NOT EXISTS transcriptions_fts USING fts5(
    transcription_id UNINDEXED,               -- Reference to transcriptions.id
    text,                                     -- Full text content for searching
    language,                                 -- Language filter
    content=transcriptions,                   -- Content table
    content_rowid=id                          -- Row ID mapping
);

-- Trigger to keep FTS index synchronized on INSERT
CREATE TRIGGER IF NOT EXISTS transcriptions_fts_insert AFTER INSERT ON transcriptions
BEGIN
    INSERT INTO transcriptions_fts(transcription_id, text, language)
    VALUES (NEW.id, NEW.text, NEW.language);
END;

-- Trigger to keep FTS index synchronized on UPDATE
CREATE TRIGGER IF NOT EXISTS transcriptions_fts_update AFTER UPDATE ON transcriptions
BEGIN
    UPDATE transcriptions_fts
    SET text = NEW.text, language = NEW.language
    WHERE transcription_id = NEW.id;
END;

-- Trigger to keep FTS index synchronized on DELETE
CREATE TRIGGER IF NOT EXISTS transcriptions_fts_delete AFTER DELETE ON transcriptions
BEGIN
    DELETE FROM transcriptions_fts WHERE transcription_id = OLD.id;
END;

-- ============================================================================
-- TRIGGER: Update updated_at timestamp automatically
-- ============================================================================
CREATE TRIGGER IF NOT EXISTS update_job_timestamp
AFTER UPDATE ON transcription_jobs
FOR EACH ROW
BEGIN
    UPDATE transcription_jobs
    SET updated_at = CURRENT_TIMESTAMP
    WHERE job_id = NEW.job_id;
END;

-- ============================================================================
-- TABLE: metadata
-- Purpose: Store schema version and migration info
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial schema version
INSERT OR REPLACE INTO schema_metadata (key, value)
VALUES ('schema_version', '001');

INSERT OR REPLACE INTO schema_metadata (key, value)
VALUES ('created_at', datetime('now'));

-- ============================================================================
-- VIEWS: Convenient query views
-- ============================================================================

-- View: Complete job information with file details
CREATE VIEW IF NOT EXISTS v_job_details AS
SELECT
    j.job_id,
    j.file_id,
    j.status,
    j.task_type,
    j.model_size,
    j.language,
    j.detected_language,
    j.language_probability,
    j.compute_type,
    j.device,
    j.duration_seconds,
    j.processing_time_seconds,
    j.created_at,
    j.updated_at,
    j.started_at,
    j.completed_at,
    f.file_hash,
    f.original_name,
    f.file_path,
    f.size_bytes,
    f.format,
    f.uploaded_at,
    t.text AS transcription_text,
    t.segment_count,
    t.srt_path
FROM transcription_jobs j
INNER JOIN files f ON j.file_id = f.id
LEFT JOIN transcriptions t ON j.job_id = t.job_id;

-- View: Job statistics summary
CREATE VIEW IF NOT EXISTS v_job_statistics AS
SELECT
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_jobs,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_jobs,
    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) AS processing_jobs,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_jobs,
    AVG(CASE WHEN processing_time_seconds IS NOT NULL THEN processing_time_seconds END) AS avg_processing_time,
    SUM(duration_seconds) AS total_audio_duration,
    COUNT(DISTINCT file_id) AS unique_files
FROM transcription_jobs;

-- ============================================================================
-- END OF MIGRATION 001
-- ============================================================================
