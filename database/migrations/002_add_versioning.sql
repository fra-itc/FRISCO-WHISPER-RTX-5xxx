-- ============================================================================
-- FRISCO WHISPER RTX 5xxx - Versioning Schema
-- Migration: 002_add_versioning.sql
-- Created: 2025-11-20
-- Description: Add transcript versioning with automatic history tracking
-- ============================================================================

-- Enable foreign key support
PRAGMA foreign_keys = ON;

-- ============================================================================
-- FIX: Recreate FTS trigger to work with versioning
-- The existing transcriptions_fts_update trigger has issues when combined
-- with versioning triggers. Since transcriptions_fts uses content=transcriptions,
-- we should use FTS5's delete/insert commands properly.
-- ============================================================================
DROP TRIGGER IF EXISTS transcriptions_fts_update;

CREATE TRIGGER transcriptions_fts_update AFTER UPDATE ON transcriptions
BEGIN
    INSERT INTO transcriptions_fts(transcriptions_fts, rowid, transcription_id, text, language)
    VALUES('delete', OLD.id, OLD.id, OLD.text, OLD.language);

    INSERT INTO transcriptions_fts(transcription_id, text, language, rowid)
    VALUES (NEW.id, NEW.text, NEW.language, NEW.id);
END;

-- ============================================================================
-- TABLE: transcript_versions
-- Purpose: Store version history for transcriptions with full audit trail
-- ============================================================================
CREATE TABLE IF NOT EXISTS transcript_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcription_id INTEGER NOT NULL,           -- Reference to original transcription
    version_number INTEGER NOT NULL,             -- Sequential version number (1, 2, 3...)
    text TEXT NOT NULL,                          -- Full text for this version
    segments TEXT NOT NULL,                      -- JSON array of segments with timestamps
    segment_count INTEGER NOT NULL DEFAULT 0,    -- Number of segments
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system',            -- User or system identifier
    change_note TEXT,                            -- Optional description of changes
    is_current BOOLEAN NOT NULL DEFAULT 0,       -- Flag for current version

    -- Foreign key constraint
    FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT chk_version_number_positive CHECK (version_number > 0),
    CONSTRAINT chk_segment_count_positive CHECK (segment_count >= 0),
    CONSTRAINT chk_is_current_boolean CHECK (is_current IN (0, 1)),

    -- Unique constraint: one version number per transcription
    CONSTRAINT uq_transcription_version UNIQUE (transcription_id, version_number)
);

-- Index for transcription_id lookups (get all versions)
CREATE INDEX IF NOT EXISTS idx_versions_transcription ON transcript_versions(transcription_id);

-- Index for version number lookups
CREATE INDEX IF NOT EXISTS idx_versions_number ON transcript_versions(transcription_id, version_number);

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_versions_created ON transcript_versions(created_at DESC);

-- Index for current version queries
CREATE INDEX IF NOT EXISTS idx_versions_current ON transcript_versions(transcription_id, is_current) WHERE is_current = 1;

-- Composite index for efficient version lookups
CREATE INDEX IF NOT EXISTS idx_versions_trans_num ON transcript_versions(transcription_id, version_number DESC);

-- ============================================================================
-- TRIGGER: Create initial version when transcription is created
-- ============================================================================
CREATE TRIGGER IF NOT EXISTS create_initial_version AFTER INSERT ON transcriptions
FOR EACH ROW
BEGIN
    INSERT INTO transcript_versions (
        transcription_id,
        version_number,
        text,
        segments,
        segment_count,
        created_by,
        change_note,
        is_current
    )
    VALUES (
        NEW.id,
        1,
        NEW.text,
        NEW.segments,
        NEW.segment_count,
        'system',
        'Initial transcription',
        1
    );
END;

-- ============================================================================
-- TRIGGER: Create new version when transcription is updated
-- ============================================================================
CREATE TRIGGER IF NOT EXISTS create_version_on_update BEFORE UPDATE OF text, segments ON transcriptions
FOR EACH ROW
WHEN OLD.text != NEW.text OR OLD.segments != NEW.segments
BEGIN
    -- Unmark previous current version
    UPDATE transcript_versions
    SET is_current = 0
    WHERE transcription_id = OLD.id AND is_current = 1;

    -- Create new version with incremented version number
    INSERT INTO transcript_versions (
        transcription_id,
        version_number,
        text,
        segments,
        segment_count,
        created_by,
        change_note,
        is_current
    )
    VALUES (
        NEW.id,
        (SELECT COALESCE(MAX(version_number), 0) + 1 FROM transcript_versions WHERE transcription_id = OLD.id),
        NEW.text,
        NEW.segments,
        NEW.segment_count,
        'system',
        'Transcription updated',
        1
    );
END;

-- ============================================================================
-- TABLE: export_formats
-- Purpose: Track export format metadata and preferences
-- ============================================================================
CREATE TABLE IF NOT EXISTS export_formats (
    format_id INTEGER PRIMARY KEY AUTOINCREMENT,
    format_name TEXT NOT NULL UNIQUE,            -- srt, vtt, json, txt, csv
    mime_type TEXT NOT NULL,                     -- MIME type for format
    file_extension TEXT NOT NULL,                -- File extension (.srt, .vtt, etc.)
    description TEXT,                            -- Format description
    is_active BOOLEAN NOT NULL DEFAULT 1,        -- Enable/disable formats

    CONSTRAINT chk_format_name CHECK (format_name IN ('srt', 'vtt', 'json', 'txt', 'csv')),
    CONSTRAINT chk_is_active_boolean CHECK (is_active IN (0, 1))
);

-- Insert supported formats
INSERT OR IGNORE INTO export_formats (format_name, mime_type, file_extension, description)
VALUES
    ('srt', 'application/x-subrip', '.srt', 'SubRip subtitle format'),
    ('vtt', 'text/vtt', '.vtt', 'WebVTT web video text tracks'),
    ('json', 'application/json', '.json', 'Structured JSON with segments'),
    ('txt', 'text/plain', '.txt', 'Plain text without timestamps'),
    ('csv', 'text/csv', '.csv', 'Comma-separated values with timestamps');

-- ============================================================================
-- TABLE: export_history
-- Purpose: Track all exports for audit trail
-- ============================================================================
CREATE TABLE IF NOT EXISTS export_history (
    export_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcription_id INTEGER NOT NULL,
    version_number INTEGER,                      -- NULL for current version
    format_name TEXT NOT NULL,
    file_path TEXT,                              -- Where file was exported
    exported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exported_by TEXT DEFAULT 'system',

    FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE CASCADE,
    FOREIGN KEY (format_name) REFERENCES export_formats(format_name)
);

-- Index for transcription export lookups
CREATE INDEX IF NOT EXISTS idx_exports_transcription ON export_history(transcription_id);

-- Index for format export queries
CREATE INDEX IF NOT EXISTS idx_exports_format ON export_history(format_name);

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_exports_time ON export_history(exported_at DESC);

-- ============================================================================
-- VIEWS: Convenient query views for versioning
-- ============================================================================

-- View: Current version of all transcriptions
CREATE VIEW IF NOT EXISTS v_current_versions AS
SELECT
    t.id AS transcription_id,
    t.job_id,
    t.language,
    t.created_at AS original_created_at,
    v.version_id,
    v.version_number,
    v.text,
    v.segments,
    v.segment_count,
    v.created_at AS version_created_at,
    v.created_by,
    v.change_note
FROM transcriptions t
INNER JOIN transcript_versions v ON t.id = v.transcription_id AND v.is_current = 1;

-- View: Version history with change details
CREATE VIEW IF NOT EXISTS v_version_history AS
SELECT
    t.id AS transcription_id,
    t.job_id,
    t.language,
    v.version_id,
    v.version_number,
    v.segment_count,
    v.created_at,
    v.created_by,
    v.change_note,
    v.is_current,
    LENGTH(v.text) AS text_length,
    -- Calculate total duration from segments (in seconds)
    (SELECT MAX(json_extract(value, '$.end'))
     FROM json_each(v.segments)) AS total_duration
FROM transcriptions t
INNER JOIN transcript_versions v ON t.id = v.transcription_id
ORDER BY t.id, v.version_number DESC;

-- View: Export statistics
CREATE VIEW IF NOT EXISTS v_export_statistics AS
SELECT
    ef.format_name,
    ef.description,
    COUNT(eh.export_id) AS export_count,
    MAX(eh.exported_at) AS last_exported,
    COUNT(DISTINCT eh.transcription_id) AS unique_transcriptions
FROM export_formats ef
LEFT JOIN export_history eh ON ef.format_name = eh.format_name
GROUP BY ef.format_name, ef.description;

-- View: Transcription version count
CREATE VIEW IF NOT EXISTS v_transcription_version_counts AS
SELECT
    t.id AS transcription_id,
    t.job_id,
    t.language,
    COUNT(v.version_id) AS version_count,
    MAX(v.version_number) AS latest_version,
    MIN(v.created_at) AS first_version_at,
    MAX(v.created_at) AS latest_version_at
FROM transcriptions t
LEFT JOIN transcript_versions v ON t.id = v.transcription_id
GROUP BY t.id, t.job_id, t.language;

-- ============================================================================
-- FUNCTION: Get version diff statistics (via view)
-- ============================================================================
CREATE VIEW IF NOT EXISTS v_version_diffs AS
SELECT
    v1.transcription_id,
    v1.version_number AS old_version,
    v2.version_number AS new_version,
    v1.text_length AS old_length,
    v2.text_length AS new_length,
    v2.text_length - v1.text_length AS length_diff,
    v1.segment_count AS old_segments,
    v2.segment_count AS new_segments,
    v2.segment_count - v1.segment_count AS segment_diff
FROM (
    SELECT
        transcription_id,
        version_number,
        LENGTH(text) AS text_length,
        segment_count
    FROM transcript_versions
) v1
INNER JOIN (
    SELECT
        transcription_id,
        version_number,
        LENGTH(text) AS text_length,
        segment_count
    FROM transcript_versions
) v2 ON v1.transcription_id = v2.transcription_id
    AND v2.version_number = v1.version_number + 1;

-- ============================================================================
-- Update schema metadata
-- ============================================================================
INSERT OR REPLACE INTO schema_metadata (key, value)
VALUES ('schema_version', '002');

INSERT OR REPLACE INTO schema_metadata (key, value)
VALUES ('migration_002_applied_at', datetime('now'));

-- ============================================================================
-- END OF MIGRATION 002
-- ============================================================================
