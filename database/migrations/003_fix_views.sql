-- ============================================================================
-- FRISCO WHISPER RTX 5xxx - Fix Views
-- Migration: 003_fix_views.sql
-- Created: 2025-11-20
-- Description: Fix v_job_details view to include file_id column
-- ============================================================================

-- Enable foreign key support
PRAGMA foreign_keys = ON;

-- ============================================================================
-- FIX: Recreate v_job_details to include file_id
-- ============================================================================
DROP VIEW IF EXISTS v_job_details;

CREATE VIEW v_job_details AS
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

-- ============================================================================
-- Update schema metadata
-- ============================================================================
INSERT OR REPLACE INTO schema_metadata (key, value)
VALUES ('schema_version', '003');

INSERT OR REPLACE INTO schema_metadata (key, value)
VALUES ('migration_003_applied_at', datetime('now'));

-- ============================================================================
-- END OF MIGRATION 003
-- ============================================================================
