#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Transcript Manager
Manages transcript storage, versioning, and format conversion
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from contextlib import contextmanager

from .database import DatabaseManager, DatabaseError
from .format_converters import FormatConverter, DiffGenerator

logger = logging.getLogger(__name__)


class TranscriptError(Exception):
    """Base exception for transcript operations"""
    pass


class TranscriptNotFoundError(TranscriptError):
    """Exception when transcript is not found"""
    pass


class VersionNotFoundError(TranscriptError):
    """Exception when version is not found"""
    pass


class TranscriptManager:
    """
    Manages transcription storage with versioning and format conversion.

    Features:
    - Save and retrieve transcripts
    - Automatic version creation on updates
    - Version history tracking
    - Rollback to previous versions
    - Compare versions
    - Export to multiple formats (SRT, VTT, JSON, TXT, CSV)
    - Version cleanup and retention policies

    Usage:
        manager = TranscriptManager(db_manager)
        transcript_id = manager.save_transcript(job_id, text, segments)
        manager.export_transcript(transcript_id, 'srt', '/path/to/output.srt')
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize transcript manager.

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db = db_manager
        self.converter = FormatConverter()
        self.diff_gen = DiffGenerator()

        # Apply versioning migration if not already applied
        self._apply_versioning_migration()

        logger.info("TranscriptManager initialized")

    def _apply_versioning_migration(self):
        """Apply versioning schema migration if not already applied."""
        migration_file = Path(__file__).parent.parent.parent / 'database' / 'migrations' / '002_add_versioning.sql'

        if not migration_file.exists():
            logger.warning(f"Versioning migration file not found: {migration_file}")
            return

        try:
            # Check if transcript_versions table exists
            cursor = self.db.connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='transcript_versions'
                """
            )
            result = cursor.fetchone()

            if result:
                logger.debug("Versioning migration already applied")
                return

            # Apply migration
            logger.info("Applying versioning migration...")
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()

            with self.db.transaction():
                self.db.connection.executescript(migration_sql)

            logger.info("Versioning migration applied successfully")

        except Exception as e:
            logger.error(f"Failed to apply versioning migration: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - allow manager to work with basic schema

    def save_transcript(
        self,
        job_id: str,
        text: str,
        segments: List[Dict[str, Any]],
        language: str = 'unknown',
        srt_path: Optional[str] = None,
        created_by: str = 'system'
    ) -> int:
        """
        Save a new transcript with automatic initial version creation.

        Args:
            job_id: Job UUID
            text: Full transcription text
            segments: List of segment dictionaries
            language: Language of transcription
            srt_path: Optional path to SRT file
            created_by: User or system identifier

        Returns:
            transcription_id: Database ID of saved transcript

        Raises:
            TranscriptError: If save fails
        """
        # Validate segments
        if not FormatConverter.validate_segments(segments):
            raise TranscriptError("Invalid segment structure")

        try:
            # Save to database (trigger will create initial version)
            transcription_id = self.db.save_transcription(
                job_id=job_id,
                text=text,
                language=language,
                segments=segments,
                srt_path=srt_path
            )

            logger.info(
                f"Transcript saved: ID={transcription_id}, job={job_id}, "
                f"segments={len(segments)}, language={language}"
            )

            return transcription_id

        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")
            raise TranscriptError(f"Failed to save transcript: {e}")

    def update_transcript(
        self,
        transcript_id: int,
        text: str,
        segments: List[Dict[str, Any]],
        created_by: str = 'system',
        change_note: Optional[str] = None
    ) -> int:
        """
        Update transcript with automatic version creation.

        Args:
            transcript_id: Transcript database ID
            text: Updated full text
            segments: Updated segments
            created_by: User or system identifier
            change_note: Optional description of changes

        Returns:
            version_number: New version number created

        Raises:
            TranscriptNotFoundError: If transcript not found
            TranscriptError: If update fails
        """
        # Validate segments
        if not FormatConverter.validate_segments(segments):
            raise TranscriptError("Invalid segment structure")

        try:
            # Get current transcript
            current = self._get_transcript_by_id(transcript_id)
            if not current:
                raise TranscriptNotFoundError(f"Transcript not found: {transcript_id}")

            segment_count = len(segments)
            segments_json = json.dumps(segments, ensure_ascii=False)

            # Update transcript (trigger will create new version)
            with self.db.transaction():
                self.db.connection.execute(
                    """
                    UPDATE transcriptions
                    SET text = ?, segments = ?, segment_count = ?
                    WHERE id = ?
                    """,
                    (text, segments_json, segment_count, transcript_id)
                )

                # Update version metadata (created_by, change_note)
                # Get the newly created version
                cursor = self.db.connection.execute(
                    """
                    SELECT version_number FROM transcript_versions
                    WHERE transcription_id = ? AND is_current = 1
                    """,
                    (transcript_id,)
                )
                result = cursor.fetchone()
                version_number = result['version_number'] if result else 1

                # Update metadata
                self.db.connection.execute(
                    """
                    UPDATE transcript_versions
                    SET created_by = ?, change_note = ?
                    WHERE transcription_id = ? AND version_number = ?
                    """,
                    (created_by, change_note or 'Transcription updated', transcript_id, version_number)
                )

            logger.info(
                f"Transcript updated: ID={transcript_id}, version={version_number}, "
                f"segments={segment_count}, by={created_by}"
            )

            return version_number

        except TranscriptNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update transcript: {e}")
            raise TranscriptError(f"Failed to update transcript: {e}")

    def get_transcript(
        self,
        transcript_id: int,
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get transcript and segments for specific version.

        Args:
            transcript_id: Transcript database ID
            version: Version number (None for current version)

        Returns:
            Dictionary with transcript details including segments

        Raises:
            TranscriptNotFoundError: If transcript or version not found
        """
        try:
            if version is None:
                # Get current version
                cursor = self.db.connection.execute(
                    """
                    SELECT
                        t.id,
                        t.job_id,
                        t.language,
                        t.srt_path,
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
                    INNER JOIN transcript_versions v
                        ON t.id = v.transcription_id AND v.is_current = 1
                    WHERE t.id = ?
                    """,
                    (transcript_id,)
                )
            else:
                # Get specific version
                cursor = self.db.connection.execute(
                    """
                    SELECT
                        t.id,
                        t.job_id,
                        t.language,
                        t.srt_path,
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
                    INNER JOIN transcript_versions v ON t.id = v.transcription_id
                    WHERE t.id = ? AND v.version_number = ?
                    """,
                    (transcript_id, version)
                )

            result = cursor.fetchone()

            if not result:
                if version:
                    raise VersionNotFoundError(
                        f"Version {version} not found for transcript {transcript_id}"
                    )
                else:
                    raise TranscriptNotFoundError(f"Transcript not found: {transcript_id}")

            # Parse segments JSON
            transcript = dict(result)
            transcript['segments'] = json.loads(transcript['segments'])

            logger.debug(
                f"Retrieved transcript: ID={transcript_id}, version={transcript['version_number']}"
            )

            return transcript

        except (TranscriptNotFoundError, VersionNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Failed to get transcript: {e}")
            raise TranscriptError(f"Failed to get transcript: {e}")

    def get_versions(self, transcript_id: int) -> List[Dict[str, Any]]:
        """
        Get all versions for a transcript.

        Args:
            transcript_id: Transcript database ID

        Returns:
            List of version dictionaries (newest first)

        Raises:
            TranscriptNotFoundError: If transcript not found
        """
        try:
            # Verify transcript exists
            if not self._get_transcript_by_id(transcript_id):
                raise TranscriptNotFoundError(f"Transcript not found: {transcript_id}")

            cursor = self.db.connection.execute(
                """
                SELECT
                    version_id,
                    version_number,
                    segment_count,
                    created_at,
                    created_by,
                    change_note,
                    is_current,
                    LENGTH(text) as text_length
                FROM transcript_versions
                WHERE transcription_id = ?
                ORDER BY version_number DESC
                """,
                (transcript_id,)
            )

            versions = [dict(row) for row in cursor.fetchall()]

            logger.debug(f"Retrieved {len(versions)} versions for transcript {transcript_id}")

            return versions

        except TranscriptNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get versions: {e}")
            raise TranscriptError(f"Failed to get versions: {e}")

    def compare_versions(
        self,
        transcript_id: int,
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """
        Compare two versions of a transcript.

        Args:
            transcript_id: Transcript database ID
            version1: First version number
            version2: Second version number

        Returns:
            Dictionary with comparison results including text and segment diffs

        Raises:
            TranscriptNotFoundError: If transcript not found
            VersionNotFoundError: If version not found
        """
        try:
            # Get both versions
            v1 = self.get_transcript(transcript_id, version1)
            v2 = self.get_transcript(transcript_id, version2)

            # Calculate text diff
            text_diff = self.diff_gen.text_diff(v1['text'], v2['text'])

            # Calculate segment diff
            segment_diff = self.diff_gen.segment_diff(v1['segments'], v2['segments'])

            comparison = {
                'transcript_id': transcript_id,
                'version1': {
                    'number': version1,
                    'created_at': v1['version_created_at'],
                    'created_by': v1['created_by'],
                    'change_note': v1['change_note']
                },
                'version2': {
                    'number': version2,
                    'created_at': v2['version_created_at'],
                    'created_by': v2['created_by'],
                    'change_note': v2['change_note']
                },
                'text_diff': text_diff,
                'segment_diff': segment_diff
            }

            logger.info(
                f"Compared versions {version1} and {version2} for transcript {transcript_id}"
            )

            return comparison

        except (TranscriptNotFoundError, VersionNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Failed to compare versions: {e}")
            raise TranscriptError(f"Failed to compare versions: {e}")

    def rollback_to_version(
        self,
        transcript_id: int,
        version_number: int,
        created_by: str = 'system',
        change_note: Optional[str] = None
    ) -> int:
        """
        Rollback transcript to a previous version (creates new version).

        Args:
            transcript_id: Transcript database ID
            version_number: Version to rollback to
            created_by: User or system identifier
            change_note: Optional note about rollback

        Returns:
            new_version_number: New version number created by rollback

        Raises:
            TranscriptNotFoundError: If transcript not found
            VersionNotFoundError: If version not found
        """
        try:
            # Get the version to rollback to
            old_version = self.get_transcript(transcript_id, version_number)

            # Create new version with old content
            note = change_note or f"Rolled back to version {version_number}"

            new_version = self.update_transcript(
                transcript_id=transcript_id,
                text=old_version['text'],
                segments=old_version['segments'],
                created_by=created_by,
                change_note=note
            )

            logger.info(
                f"Rolled back transcript {transcript_id} to version {version_number}, "
                f"created new version {new_version}"
            )

            return new_version

        except (TranscriptNotFoundError, VersionNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Failed to rollback version: {e}")
            raise TranscriptError(f"Failed to rollback version: {e}")

    def export_transcript(
        self,
        transcript_id: int,
        format_name: str,
        output_path: Optional[str] = None,
        version: Optional[int] = None,
        **format_options
    ) -> str:
        """
        Export transcript to specified format.

        Args:
            transcript_id: Transcript database ID
            format_name: Output format (srt, vtt, json, txt, csv)
            output_path: Optional path to save file
            version: Version number (None for current)
            **format_options: Additional format-specific options

        Returns:
            Formatted content string (and saves to file if output_path provided)

        Raises:
            TranscriptNotFoundError: If transcript not found
            ValueError: If format is not supported
        """
        try:
            # Get transcript
            transcript = self.get_transcript(transcript_id, version)

            # Add metadata for certain formats
            if format_name.lower() in ['vtt', 'json']:
                metadata = {
                    'language': transcript['language'],
                    'job_id': transcript['job_id'],
                    'version': transcript['version_number']
                }
                format_options['metadata'] = metadata

            if format_name.lower() == 'json':
                format_options['text'] = transcript['text']

            # Convert to format
            content = self.converter.convert(
                transcript['segments'],
                format_name,
                **format_options
            )

            # Save to file if path provided
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Record export in history
                self._record_export(
                    transcript_id=transcript_id,
                    version_number=version,
                    format_name=format_name,
                    file_path=str(output_file)
                )

                logger.info(
                    f"Exported transcript {transcript_id} v{transcript['version_number']} "
                    f"to {format_name}: {output_file}"
                )
            else:
                logger.debug(
                    f"Generated {format_name} format for transcript {transcript_id} "
                    f"v{transcript['version_number']}"
                )

            return content

        except (TranscriptNotFoundError, VersionNotFoundError):
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to export transcript: {e}")
            raise TranscriptError(f"Failed to export transcript: {e}")

    def delete_old_versions(
        self,
        transcript_id: int,
        keep_count: int = 5
    ) -> int:
        """
        Delete old versions, keeping only the most recent N versions.

        Args:
            transcript_id: Transcript database ID
            keep_count: Number of recent versions to keep

        Returns:
            Number of versions deleted

        Raises:
            TranscriptNotFoundError: If transcript not found
        """
        if keep_count < 1:
            raise ValueError("keep_count must be at least 1")

        try:
            # Verify transcript exists
            if not self._get_transcript_by_id(transcript_id):
                raise TranscriptNotFoundError(f"Transcript not found: {transcript_id}")

            with self.db.transaction():
                # Delete old versions (keep most recent N)
                cursor = self.db.connection.execute(
                    """
                    DELETE FROM transcript_versions
                    WHERE transcription_id = ?
                    AND version_number NOT IN (
                        SELECT version_number
                        FROM transcript_versions
                        WHERE transcription_id = ?
                        ORDER BY version_number DESC
                        LIMIT ?
                    )
                    """,
                    (transcript_id, transcript_id, keep_count)
                )

                deleted_count = cursor.rowcount

            logger.info(
                f"Deleted {deleted_count} old versions for transcript {transcript_id}, "
                f"keeping {keep_count} most recent"
            )

            return deleted_count

        except TranscriptNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete old versions: {e}")
            raise TranscriptError(f"Failed to delete old versions: {e}")

    def get_version_history(self, transcript_id: int) -> Dict[str, Any]:
        """
        Get complete version history with metadata and statistics.

        Args:
            transcript_id: Transcript database ID

        Returns:
            Dictionary with transcript info and version history

        Raises:
            TranscriptNotFoundError: If transcript not found
        """
        try:
            # Get transcript info
            transcript = self._get_transcript_by_id(transcript_id)
            if not transcript:
                raise TranscriptNotFoundError(f"Transcript not found: {transcript_id}")

            # Get all versions
            versions = self.get_versions(transcript_id)

            # Get export history
            cursor = self.db.connection.execute(
                """
                SELECT
                    format_name,
                    version_number,
                    file_path,
                    exported_at,
                    exported_by
                FROM export_history
                WHERE transcription_id = ?
                ORDER BY exported_at DESC
                """,
                (transcript_id,)
            )
            exports = [dict(row) for row in cursor.fetchall()]

            history = {
                'transcript_id': transcript_id,
                'job_id': transcript['job_id'],
                'language': transcript['language'],
                'created_at': transcript['created_at'],
                'version_count': len(versions),
                'current_version': next((v['version_number'] for v in versions if v['is_current']), None),
                'versions': versions,
                'export_count': len(exports),
                'exports': exports
            }

            logger.debug(f"Retrieved version history for transcript {transcript_id}")

            return history

        except TranscriptNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get version history: {e}")
            raise TranscriptError(f"Failed to get version history: {e}")

    def get_transcript_by_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current transcript for a job.

        Args:
            job_id: Job UUID

        Returns:
            Transcript dictionary or None if not found
        """
        try:
            cursor = self.db.connection.execute(
                """
                SELECT id FROM transcriptions WHERE job_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (job_id,)
            )
            result = cursor.fetchone()

            if result:
                return self.get_transcript(result['id'])
            return None

        except Exception as e:
            logger.error(f"Failed to get transcript by job: {e}")
            return None

    def _get_transcript_by_id(self, transcript_id: int) -> Optional[Dict[str, Any]]:
        """
        Get basic transcript info (without segments).

        Args:
            transcript_id: Transcript database ID

        Returns:
            Transcript dictionary or None if not found
        """
        cursor = self.db.connection.execute(
            "SELECT * FROM transcriptions WHERE id = ?",
            (transcript_id,)
        )
        result = cursor.fetchone()
        return dict(result) if result else None

    def _record_export(
        self,
        transcript_id: int,
        version_number: Optional[int],
        format_name: str,
        file_path: str,
        exported_by: str = 'system'
    ):
        """
        Record export in history table.

        Args:
            transcript_id: Transcript database ID
            version_number: Version exported (None for current)
            format_name: Format name
            file_path: Export file path
            exported_by: User or system identifier
        """
        try:
            with self.db.transaction():
                self.db.connection.execute(
                    """
                    INSERT INTO export_history (
                        transcription_id, version_number, format_name,
                        file_path, exported_by
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (transcript_id, version_number, format_name, file_path, exported_by)
                )
        except Exception as e:
            logger.warning(f"Failed to record export history: {e}")
            # Don't raise - export was successful even if logging failed

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get transcript and versioning statistics.

        Returns:
            Dictionary with various statistics
        """
        try:
            # Transcript counts
            cursor = self.db.connection.execute(
                "SELECT COUNT(*) as total_transcripts FROM transcriptions"
            )
            stats = dict(cursor.fetchone())

            # Version counts
            cursor = self.db.connection.execute(
                """
                SELECT
                    COUNT(*) as total_versions,
                    AVG(version_count) as avg_versions_per_transcript,
                    MAX(version_count) as max_versions
                FROM (
                    SELECT transcription_id, COUNT(*) as version_count
                    FROM transcript_versions
                    GROUP BY transcription_id
                )
                """
            )
            stats.update(dict(cursor.fetchone()))

            # Export counts
            cursor = self.db.connection.execute(
                """
                SELECT
                    COUNT(*) as total_exports,
                    COUNT(DISTINCT format_name) as formats_used
                FROM export_history
                """
            )
            stats.update(dict(cursor.fetchone()))

            # Format breakdown
            cursor = self.db.connection.execute(
                """
                SELECT format_name, COUNT(*) as count
                FROM export_history
                GROUP BY format_name
                ORDER BY count DESC
                """
            )
            stats['exports_by_format'] = {row['format_name']: row['count'] for row in cursor.fetchall()}

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
