#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Database Manager
Handles SQLite database operations for transcription job management
"""

import sqlite3
import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception for connection-related errors"""
    pass


class DatabaseIntegrityError(DatabaseError):
    """Exception for data integrity errors"""
    pass


class DatabaseManager:
    """
    Thread-safe database manager for transcription jobs and results.

    Features:
    - Connection pooling with thread-local storage
    - Automatic schema initialization and migrations
    - Full-text search support
    - Atomic transactions with proper error handling
    - Duplicate file detection via SHA256 hashing

    Usage:
        db = DatabaseManager('database/transcription.db')
        job_id = db.create_job(file_path='audio.mp3', model_size='medium')
        db.update_job(job_id, status='completed')
    """

    def __init__(self, db_path: str = 'database/transcription.db', pool_size: int = 5):
        """
        Initialize database manager with connection pooling.

        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections in pool (unused for now, kept for future)
        """
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self._local = threading.local()

        # Create database directory if not exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self.init_db()

        logger.info(f"DatabaseManager initialized: {self.db_path}")

    @property
    def connection(self) -> sqlite3.Connection:
        """
        Get thread-local database connection.
        Creates new connection if none exists for current thread.
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = self._create_connection()
        return self._local.conn

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings."""
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None  # Autocommit mode, we'll handle transactions manually
            )

            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")

            # Performance optimizations
            conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous = NORMAL")  # Balance safety/performance
            conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
            conn.execute("PRAGMA temp_store = MEMORY")  # Store temp tables in memory

            # Row factory for dict-like access
            conn.row_factory = sqlite3.Row

            logger.debug("Database connection created")
            return conn

        except sqlite3.Error as e:
            logger.error(f"Failed to create database connection: {e}")
            raise DatabaseConnectionError(f"Cannot connect to database: {e}")

    @contextmanager
    def transaction(self):
        """
        Context manager for atomic database transactions.

        Usage:
            with db.transaction():
                db.create_job(...)
                db.update_job(...)
        """
        conn = self.connection
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise

    def init_db(self):
        """Initialize database schema from migration file."""
        migration_file = Path(__file__).parent.parent.parent / 'database' / 'migrations' / '001_initial_schema.sql'

        if not migration_file.exists():
            raise DatabaseError(f"Migration file not found: {migration_file}")

        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()

            with self.transaction():
                self.connection.executescript(schema_sql)

            logger.info("Database schema initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Calculate SHA256 hash of a file for duplicate detection.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA256 hash
        """
        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            return sha256_hash.hexdigest()

        except Exception as e:
            logger.error(f"Failed to calculate file hash: {e}")
            raise DatabaseError(f"Cannot calculate file hash: {e}")

    def add_or_get_file(self, file_path: str) -> Tuple[int, bool]:
        """
        Add file to database or get existing file ID if duplicate exists.

        Args:
            file_path: Path to audio file

        Returns:
            Tuple of (file_id, is_new) where is_new indicates if file was newly added
        """
        path = Path(file_path)

        if not path.exists():
            raise DatabaseError(f"File not found: {file_path}")

        # Calculate file hash
        file_hash = self.calculate_file_hash(file_path)
        file_size = path.stat().st_size
        file_format = path.suffix.lstrip('.').lower()

        # Check if file already exists
        cursor = self.connection.execute(
            "SELECT id FROM files WHERE file_hash = ?",
            (file_hash,)
        )
        existing = cursor.fetchone()

        if existing:
            logger.info(f"Duplicate file detected: {path.name} (hash: {file_hash[:8]}...)")
            return existing['id'], False

        # Add new file
        try:
            with self.transaction():
                cursor = self.connection.execute(
                    """
                    INSERT INTO files (file_hash, original_name, file_path, size_bytes, format)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (file_hash, path.name, str(path.absolute()), file_size, file_format)
                )
                file_id = cursor.lastrowid

            logger.info(f"File added to database: {path.name} (ID: {file_id})")
            return file_id, True

        except sqlite3.IntegrityError as e:
            logger.error(f"File integrity error: {e}")
            raise DatabaseIntegrityError(f"Failed to add file: {e}")

    def create_job(
        self,
        file_path: str,
        model_size: str,
        task_type: str = 'transcribe',
        language: Optional[str] = None,
        compute_type: Optional[str] = None,
        device: Optional[str] = None,
        beam_size: int = 5,
        duration_seconds: Optional[float] = None
    ) -> str:
        """
        Create a new transcription job.

        Args:
            file_path: Path to audio file
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
            task_type: 'transcribe' or 'translate'
            language: Source language code (None for auto-detect)
            compute_type: Computation type (float16, float32, int8)
            device: Device to use ('cuda' or 'cpu')
            beam_size: Beam search size for transcription
            duration_seconds: Audio duration in seconds

        Returns:
            job_id: UUID string for the created job
        """
        file_id, is_new = self.add_or_get_file(file_path)
        job_id = str(uuid.uuid4())
        file_name = Path(file_path).name

        try:
            with self.transaction():
                self.connection.execute(
                    """
                    INSERT INTO transcription_jobs (
                        job_id, file_id, file_name, model_size, status, task_type,
                        language, compute_type, device, beam_size, duration_seconds
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id, file_id, file_name, model_size, 'pending', task_type,
                        language, compute_type, device, beam_size, duration_seconds
                    )
                )

            logger.info(f"Job created: {job_id} for file: {file_name}")
            return job_id

        except sqlite3.IntegrityError as e:
            logger.error(f"Job creation integrity error: {e}")
            raise DatabaseIntegrityError(f"Failed to create job: {e}")

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        detected_language: Optional[str] = None,
        language_probability: Optional[float] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        processing_time_seconds: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update job status and metadata.

        Args:
            job_id: Job UUID
            status: New status (pending, processing, completed, failed)
            detected_language: Auto-detected language
            language_probability: Confidence of language detection
            started_at: Processing start timestamp
            completed_at: Processing completion timestamp
            processing_time_seconds: Time taken to process
            error_message: Error details if failed

        Returns:
            True if update successful, False otherwise
        """
        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)

        if detected_language:
            updates.append("detected_language = ?")
            params.append(detected_language)

        if language_probability is not None:
            updates.append("language_probability = ?")
            params.append(language_probability)

        if started_at:
            updates.append("started_at = ?")
            params.append(started_at.isoformat())

        if completed_at:
            updates.append("completed_at = ?")
            params.append(completed_at.isoformat())

        if processing_time_seconds is not None:
            updates.append("processing_time_seconds = ?")
            params.append(processing_time_seconds)

        if error_message:
            updates.append("error_message = ?")
            params.append(error_message)

        if not updates:
            logger.warning(f"No updates provided for job {job_id}")
            return False

        params.append(job_id)
        sql = f"UPDATE transcription_jobs SET {', '.join(updates)} WHERE job_id = ?"

        try:
            with self.transaction():
                cursor = self.connection.execute(sql, tuple(params))

            if cursor.rowcount == 0:
                logger.warning(f"Job not found: {job_id}")
                return False

            logger.info(f"Job updated: {job_id} - {dict(zip([u.split('=')[0].strip() for u in updates], params[:-1]))}")
            return True

        except Exception as e:
            logger.error(f"Failed to update job: {e}")
            raise DatabaseError(f"Job update failed: {e}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job details by ID.

        Args:
            job_id: Job UUID

        Returns:
            Dictionary with job details or None if not found
        """
        cursor = self.connection.execute(
            "SELECT * FROM v_job_details WHERE job_id = ?",
            (job_id,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_jobs_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get jobs by status.

        Args:
            status: Job status (pending, processing, completed, failed)
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries
        """
        cursor = self.connection.execute(
            "SELECT * FROM v_job_details WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get most recent jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries
        """
        cursor = self.connection.execute(
            "SELECT * FROM v_job_details ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def save_transcription(
        self,
        job_id: str,
        text: str,
        language: str,
        segments: List[Dict[str, Any]],
        srt_path: Optional[str] = None
    ) -> int:
        """
        Save transcription results.

        Args:
            job_id: Job UUID
            text: Full transcription text
            language: Language of transcription
            segments: List of segment dictionaries with timestamps and text
            srt_path: Optional path to generated SRT file

        Returns:
            transcription_id: Database ID of saved transcription
        """
        segment_count = len(segments)
        segments_json = json.dumps(segments, ensure_ascii=False)

        try:
            with self.transaction():
                cursor = self.connection.execute(
                    """
                    INSERT INTO transcriptions (job_id, text, language, segment_count, segments, srt_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (job_id, text, language, segment_count, segments_json, srt_path)
                )
                transcription_id = cursor.lastrowid

            logger.info(f"Transcription saved: ID={transcription_id}, segments={segment_count}, language={language}")
            return transcription_id

        except Exception as e:
            logger.error(f"Failed to save transcription: {e}")
            raise DatabaseError(f"Transcription save failed: {e}")

    def get_transcriptions(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get all transcriptions for a job.

        Args:
            job_id: Job UUID

        Returns:
            List of transcription dictionaries
        """
        cursor = self.connection.execute(
            "SELECT * FROM transcriptions WHERE job_id = ? ORDER BY created_at DESC",
            (job_id,)
        )

        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parse JSON segments
            if result.get('segments'):
                result['segments'] = json.loads(result['segments'])
            results.append(result)

        return results

    def search_transcriptions(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Full-text search in transcriptions.

        Args:
            query: Search query text
            language: Optional language filter
            limit: Maximum results to return

        Returns:
            List of matching transcription dictionaries with highlights
        """
        if language:
            sql = """
                SELECT t.*, snippet(transcriptions_fts, 1, '<mark>', '</mark>', '...', 64) AS snippet
                FROM transcriptions t
                JOIN transcriptions_fts fts ON t.id = fts.transcription_id
                WHERE transcriptions_fts MATCH ? AND t.language = ?
                ORDER BY rank
                LIMIT ?
            """
            params = (query, language, limit)
        else:
            sql = """
                SELECT t.*, snippet(transcriptions_fts, 1, '<mark>', '</mark>', '...', 64) AS snippet
                FROM transcriptions t
                JOIN transcriptions_fts fts ON t.id = fts.transcription_id
                WHERE transcriptions_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            params = (query, limit)

        cursor = self.connection.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parse JSON segments
            if result.get('segments'):
                result['segments'] = json.loads(result['segments'])
            results.append(result)

        logger.info(f"Search query '{query}' returned {len(results)} results")
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with various statistics
        """
        cursor = self.connection.execute("SELECT * FROM v_job_statistics")
        stats = dict(cursor.fetchone())

        # Add file statistics
        cursor = self.connection.execute(
            "SELECT COUNT(*) as total_files, SUM(size_bytes) as total_size FROM files"
        )
        file_stats = dict(cursor.fetchone())
        stats.update(file_stats)

        return stats

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job and its associated transcriptions (cascade).

        Args:
            job_id: Job UUID

        Returns:
            True if deleted successfully
        """
        try:
            with self.transaction():
                cursor = self.connection.execute(
                    "DELETE FROM transcription_jobs WHERE job_id = ?",
                    (job_id,)
                )

            if cursor.rowcount == 0:
                logger.warning(f"Job not found for deletion: {job_id}")
                return False

            logger.info(f"Job deleted: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete job: {e}")
            raise DatabaseError(f"Job deletion failed: {e}")

    def cleanup_old_jobs(self, days: int = 30, status: str = 'completed') -> int:
        """
        Delete old jobs older than specified days.

        Args:
            days: Number of days to keep
            status: Status of jobs to clean up

        Returns:
            Number of jobs deleted
        """
        try:
            with self.transaction():
                cursor = self.connection.execute(
                    """
                    DELETE FROM transcription_jobs
                    WHERE status = ? AND created_at < datetime('now', '-' || ? || ' days')
                    """,
                    (status, days)
                )
                deleted_count = cursor.rowcount

            logger.info(f"Cleaned up {deleted_count} old jobs (status={status}, older than {days} days)")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            raise DatabaseError(f"Job cleanup failed: {e}")

    def close(self):
        """Close database connection for current thread."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            logger.debug("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.close()
        return False
