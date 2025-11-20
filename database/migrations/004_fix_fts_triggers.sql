-- ============================================================================
-- FRISCO WHISPER RTX 5xxx - Fix FTS Triggers
-- Migration: 004_fix_fts_triggers.sql
-- Created: 2025-11-20
-- Description: Fix FTS5 triggers to use correct rowid reference
-- ============================================================================

-- Enable foreign key support
PRAGMA foreign_keys = ON;

-- ============================================================================
-- FIX: Recreate FTS triggers to use rowid correctly
-- For content FTS5 tables, we should reference rowid, not transcription_id
-- ============================================================================

DROP TRIGGER IF EXISTS transcriptions_fts_insert;
DROP TRIGGER IF EXISTS transcriptions_fts_update;
DROP TRIGGER IF EXISTS transcriptions_fts_delete;

-- Trigger to keep FTS index synchronized on INSERT
-- For content FTS5 tables, FTS automatically syncs on INSERT
CREATE TRIGGER transcriptions_fts_insert AFTER INSERT ON transcriptions
BEGIN
    INSERT INTO transcriptions_fts(transcription_id, text, language)
    VALUES (NEW.id, NEW.text, NEW.language);
END;

-- Trigger to keep FTS index synchronized on UPDATE
-- Use FTS5 delete/insert commands for proper synchronization
CREATE TRIGGER transcriptions_fts_update AFTER UPDATE ON transcriptions
BEGIN
    INSERT INTO transcriptions_fts(transcriptions_fts, rowid, transcription_id, text, language)
    VALUES('delete', OLD.id, OLD.id, OLD.text, OLD.language);

    INSERT INTO transcriptions_fts(transcription_id, text, language)
    VALUES (NEW.id, NEW.text, NEW.language);
END;

-- Trigger to keep FTS index synchronized on DELETE
-- For content FTS5 tables, use FTS5 delete command
CREATE TRIGGER transcriptions_fts_delete AFTER DELETE ON transcriptions
BEGIN
    INSERT INTO transcriptions_fts(transcriptions_fts, rowid, transcription_id, text, language)
    VALUES('delete', OLD.id, OLD.id, OLD.text, OLD.language);
END;

-- ============================================================================
-- Update schema metadata
-- ============================================================================
INSERT OR REPLACE INTO schema_metadata (key, value)
VALUES ('schema_version', '004');

INSERT OR REPLACE INTO schema_metadata (key, value)
VALUES ('migration_004_applied_at', datetime('now'));

-- ============================================================================
-- END OF MIGRATION 004
-- ============================================================================
