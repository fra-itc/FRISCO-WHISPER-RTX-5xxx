#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - File Manager
Comprehensive file management system with duplicate detection and storage optimization
"""

import hashlib
import shutil
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, BinaryIO
import logging
import threading
from contextlib import contextmanager
import json

from .database import DatabaseManager, DatabaseError
from . import storage_config as config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class FileManagerError(Exception):
    """Base exception for file manager errors"""
    pass


class FileNotFoundError(FileManagerError):
    """File not found error"""
    pass


class FileSizeError(FileManagerError):
    """File size validation error"""
    pass


class FileFormatError(FileManagerError):
    """File format validation error"""
    pass


class StorageQuotaError(FileManagerError):
    """Storage quota exceeded error"""
    pass


class DuplicateFileError(FileManagerError):
    """Duplicate file detected (when strict mode enabled)"""
    pass


# ============================================================================
# File Manager Class
# ============================================================================

class FileManager:
    """
    Comprehensive file management system with deduplication and metadata tracking.

    Features:
    - Hash-based duplicate detection (SHA256)
    - Organized storage structure (year/month/hash.ext)
    - Format validation and MIME type checking
    - Storage quota management
    - Reference counting for safe deletion
    - Automatic cleanup of orphaned files
    - Thread-safe operations
    - File archiving and retention policies

    Usage:
        fm = FileManager(db_manager)
        file_id, is_new = fm.upload_file(file_data, 'audio.mp3')
        file_info = fm.get_file(file_id)
        fm.delete_file(file_id)
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        base_dir: Optional[Path] = None
    ):
        """
        Initialize file manager.

        Args:
            db_manager: Database manager instance
            base_dir: Optional base directory override
        """
        self.db = db_manager
        self.base_dir = base_dir or config.UPLOAD_BASE_DIR
        self._lock = threading.RLock()

        # Ensure base directories exist
        self._ensure_directories()

        logger.info(f"FileManager initialized: {self.base_dir}")

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        for directory in [self.base_dir, config.ARCHIVE_DIR, config.TEMP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {directory}")

    @staticmethod
    def calculate_hash(file_path: Path) -> str:
        """
        Calculate SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA256 hash

        Raises:
            FileManagerError: If hash calculation fails
        """
        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(config.HASH_CHUNK_SIZE), b""):
                    sha256_hash.update(byte_block)

            return sha256_hash.hexdigest()

        except Exception as e:
            logger.error(f"Failed to calculate file hash: {e}")
            raise FileManagerError(f"Cannot calculate file hash: {e}")

    @staticmethod
    def calculate_hash_from_data(file_data: BinaryIO) -> str:
        """
        Calculate SHA256 hash from file data stream.

        Args:
            file_data: Binary file stream

        Returns:
            Hex string of SHA256 hash
        """
        sha256_hash = hashlib.sha256()

        # Save current position
        current_pos = file_data.tell()

        # Read from beginning
        file_data.seek(0)

        for byte_block in iter(lambda: file_data.read(config.HASH_CHUNK_SIZE), b""):
            sha256_hash.update(byte_block)

        # Restore position
        file_data.seek(current_pos)

        return sha256_hash.hexdigest()

    def validate_file_format(self, file_path: Path) -> bool:
        """
        Validate file format is supported.

        Args:
            file_path: Path to file

        Returns:
            True if format is valid

        Raises:
            FileFormatError: If format is not supported
        """
        extension = file_path.suffix.lstrip('.').lower()

        if not config.is_format_supported(extension):
            raise FileFormatError(
                f"Unsupported file format: {extension}. "
                f"Supported formats: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )

        # Optional: Validate MIME type
        if config.VALIDATE_AUDIO_HEADERS:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            expected_mimes = config.get_mime_types(extension)

            if mime_type and expected_mimes and mime_type not in expected_mimes:
                logger.warning(
                    f"MIME type mismatch: got {mime_type}, "
                    f"expected one of {expected_mimes}"
                )

        return True

    def validate_file_size(self, file_path: Path) -> bool:
        """
        Validate file size is within limits.

        Args:
            file_path: Path to file

        Returns:
            True if size is valid

        Raises:
            FileSizeError: If file size is invalid
        """
        size = file_path.stat().st_size

        if size < config.MIN_FILE_SIZE:
            raise FileSizeError(
                f"File too small: {config.format_file_size(size)} "
                f"(minimum: {config.format_file_size(config.MIN_FILE_SIZE)})"
            )

        if size > config.MAX_FILE_SIZE:
            raise FileSizeError(
                f"File too large: {config.format_file_size(size)} "
                f"(maximum: {config.format_file_size(config.MAX_FILE_SIZE)})"
            )

        if size > config.LARGE_FILE_WARNING:
            logger.warning(
                f"Large file detected: {config.format_file_size(size)} "
                f"for {file_path.name}"
            )

        return True

    def check_storage_quota(self, additional_size: int = 0) -> Dict[str, Any]:
        """
        Check storage quota status.

        Args:
            additional_size: Additional bytes to account for

        Returns:
            Dictionary with quota information

        Raises:
            StorageQuotaError: If quota exceeded
        """
        stats = self.get_storage_stats()
        total_used = stats['total_size_bytes'] + additional_size

        quota_info = {
            'current_usage': stats['total_size_bytes'],
            'additional': additional_size,
            'total_after': total_used,
            'quota_max': config.STORAGE_QUOTA_MAX,
            'percentage_used': config.calculate_storage_percentage(total_used),
            'is_warning': config.is_storage_warning(total_used),
            'is_critical': config.is_storage_critical(total_used)
        }

        if total_used > config.STORAGE_QUOTA_MAX:
            raise StorageQuotaError(
                f"Storage quota exceeded: "
                f"{config.format_file_size(total_used)} / "
                f"{config.format_file_size(config.STORAGE_QUOTA_MAX)}"
            )

        if quota_info['is_critical']:
            logger.error(f"Storage critical: {quota_info['percentage_used']:.1f}% used")
        elif quota_info['is_warning']:
            logger.warning(f"Storage warning: {quota_info['percentage_used']:.1f}% used")

        return quota_info

    def _generate_storage_path(self, file_hash: str, extension: str) -> Path:
        """
        Generate organized storage path for file.

        Args:
            file_hash: SHA256 hash of file
            extension: File extension

        Returns:
            Path object for file storage
        """
        now = datetime.now()

        if config.USE_HASH_AS_FILENAME:
            filename = f"{file_hash}.{extension}"
        else:
            filename = f"{file_hash[:16]}_{now.strftime('%Y%m%d%H%M%S')}.{extension}"

        return config.get_upload_path(now.year, now.month, filename)

    def upload_file(
        self,
        file_path: str,
        original_name: Optional[str] = None,
        skip_duplicate_check: bool = False
    ) -> Tuple[int, bool]:
        """
        Upload file with automatic deduplication.

        Args:
            file_path: Path to file to upload
            original_name: Original filename (optional, defaults to file_path name)
            skip_duplicate_check: Skip duplicate check (faster, but no dedup)

        Returns:
            Tuple of (file_id, is_new) where is_new indicates if file was newly added

        Raises:
            FileManagerError: If upload fails
            FileNotFoundError: If file doesn't exist
            FileSizeError: If file size invalid
            FileFormatError: If file format invalid
            StorageQuotaError: If quota exceeded
        """
        source_path = Path(file_path)

        # Validate file exists
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate format and size
        self.validate_file_format(source_path)
        self.validate_file_size(source_path)

        # Check storage quota
        file_size = source_path.stat().st_size
        self.check_storage_quota(file_size)

        # Calculate file hash
        file_hash = self.calculate_hash(source_path)
        extension = source_path.suffix.lstrip('.').lower()
        original_name = original_name or source_path.name

        with self._lock:
            # Check for duplicate
            if not skip_duplicate_check and config.CHECK_DUPLICATES:
                existing = self.get_file_by_hash(file_hash)
                if existing:
                    logger.info(
                        f"Duplicate file detected: {original_name} "
                        f"(hash: {file_hash[:8]}..., existing ID: {existing['id']})"
                    )
                    return existing['id'], False

            # Generate storage path
            storage_path = self._generate_storage_path(file_hash, extension)
            storage_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                # Copy file to storage
                shutil.copy2(source_path, storage_path)
                logger.info(f"File copied to storage: {storage_path}")

                # Verify hash if configured
                if config.VERIFY_UPLOAD_HASH:
                    verify_hash = self.calculate_hash(storage_path)
                    if verify_hash != file_hash:
                        storage_path.unlink()
                        raise FileManagerError(
                            f"Hash verification failed: {file_hash} != {verify_hash}"
                        )

                # Add to database (pass original_name to preserve it)
                file_id, is_new = self.db.add_or_get_file(
                    str(storage_path.absolute()),
                    original_name=original_name
                )

                if is_new:
                    logger.info(
                        f"File uploaded successfully: {original_name} "
                        f"(ID: {file_id}, size: {config.format_file_size(file_size)})"
                    )
                else:
                    logger.info(f"File already exists in database: {original_name} (ID: {file_id})")

                return file_id, is_new

            except Exception as e:
                # Cleanup on failure
                if storage_path.exists():
                    storage_path.unlink()
                logger.error(f"File upload failed: {e}")
                raise FileManagerError(f"Upload failed: {e}")

    def get_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get file information by ID.

        Args:
            file_id: File database ID

        Returns:
            Dictionary with file information or None if not found
        """
        cursor = self.db.connection.execute(
            "SELECT * FROM files WHERE id = ?",
            (file_id,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_file_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        Find file by hash.

        Args:
            file_hash: SHA256 hash

        Returns:
            Dictionary with file information or None if not found
        """
        cursor = self.db.connection.execute(
            "SELECT * FROM files WHERE file_hash = ?",
            (file_hash,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_file_path(self, file_id: int) -> Optional[Path]:
        """
        Get absolute file path.

        Args:
            file_id: File database ID

        Returns:
            Path object or None if not found
        """
        file_info = self.get_file(file_id)
        if file_info:
            return Path(file_info['file_path'])
        return None

    def list_files(
        self,
        limit: int = 100,
        offset: int = 0,
        format_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        order_by: str = 'uploaded_at',
        order_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List files with pagination and filtering.

        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip
            format_filter: Filter by format (e.g., 'mp3', 'wav')
            date_from: Filter files uploaded after this date
            date_to: Filter files uploaded before this date
            order_by: Column to order by
            order_desc: Order descending if True

        Returns:
            List of file dictionaries
        """
        sql_parts = ["SELECT * FROM files WHERE 1=1"]
        params = []

        # Apply filters
        if format_filter:
            sql_parts.append("AND format = ?")
            params.append(format_filter.lower())

        if date_from:
            sql_parts.append("AND uploaded_at >= ?")
            params.append(date_from.isoformat())

        if date_to:
            sql_parts.append("AND uploaded_at <= ?")
            params.append(date_to.isoformat())

        # Order
        order_direction = "DESC" if order_desc else "ASC"
        sql_parts.append(f"ORDER BY {order_by} {order_direction}")

        # Pagination
        sql_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        sql = " ".join(sql_parts)
        cursor = self.db.connection.execute(sql, tuple(params))

        return [dict(row) for row in cursor.fetchall()]

    def count_file_references(self, file_id: int) -> int:
        """
        Count how many jobs reference this file.

        Args:
            file_id: File database ID

        Returns:
            Number of jobs referencing this file
        """
        cursor = self.db.connection.execute(
            "SELECT COUNT(*) as count FROM transcription_jobs WHERE file_id = ?",
            (file_id,)
        )
        result = cursor.fetchone()
        return result['count'] if result else 0

    def delete_file(
        self,
        file_id: int,
        force: bool = False,
        skip_physical: bool = False
    ) -> bool:
        """
        Delete file with reference checking.

        Args:
            file_id: File database ID
            force: Force deletion even if references exist
            skip_physical: Only delete database record, keep physical file

        Returns:
            True if deleted successfully

        Raises:
            FileManagerError: If file has references and force=False
        """
        with self._lock:
            # Get file info
            file_info = self.get_file(file_id)
            if not file_info:
                logger.warning(f"File not found for deletion: {file_id}")
                return False

            # Check references
            ref_count = self.count_file_references(file_id)
            if ref_count > 0 and not force:
                raise FileManagerError(
                    f"Cannot delete file {file_id}: {ref_count} job(s) reference it. "
                    f"Use force=True to delete anyway."
                )

            try:
                # Delete physical file
                if not skip_physical:
                    file_path = Path(file_info['file_path'])
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Physical file deleted: {file_path}")

                # Delete from database
                with self.db.transaction():
                    self.db.connection.execute(
                        "DELETE FROM files WHERE id = ?",
                        (file_id,)
                    )

                logger.info(f"File deleted from database: ID={file_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to delete file: {e}")
                raise FileManagerError(f"File deletion failed: {e}")

    def cleanup_orphaned_files(
        self,
        min_age_days: int = config.ORPHANED_FILE_ARCHIVE_DAYS,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Remove files not referenced by any jobs.

        Args:
            min_age_days: Minimum age in days before file can be deleted
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_date = datetime.now() - timedelta(days=min_age_days)

        # Find orphaned files
        cursor = self.db.connection.execute(
            """
            SELECT f.*
            FROM files f
            LEFT JOIN transcription_jobs j ON f.id = j.file_id
            WHERE j.file_id IS NULL
            AND f.uploaded_at < ?
            """,
            (cutoff_date.isoformat(),)
        )

        orphaned = [dict(row) for row in cursor.fetchall()]
        deleted_count = 0
        freed_bytes = 0
        errors = []

        for file_info in orphaned:
            try:
                if not dry_run:
                    self.delete_file(file_info['id'], force=True)
                    deleted_count += 1

                freed_bytes += file_info['size_bytes']

            except Exception as e:
                errors.append({
                    'file_id': file_info['id'],
                    'error': str(e)
                })
                logger.error(f"Failed to delete orphaned file {file_info['id']}: {e}")

        results = {
            'found': len(orphaned),
            'deleted': deleted_count,
            'freed_bytes': freed_bytes,
            'freed_formatted': config.format_file_size(freed_bytes),
            'errors': errors,
            'dry_run': dry_run
        }

        logger.info(
            f"Orphaned file cleanup: {deleted_count}/{len(orphaned)} deleted, "
            f"{config.format_file_size(freed_bytes)} freed"
        )

        return results

    def archive_old_files(
        self,
        days: int = config.DEFAULT_ARCHIVE_DAYS,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Archive files older than N days.

        Args:
            days: Archive files older than this many days
            dry_run: If True, only report what would be archived

        Returns:
            Dictionary with archive statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Find old files
        cursor = self.db.connection.execute(
            "SELECT * FROM files WHERE uploaded_at < ?",
            (cutoff_date.isoformat(),)
        )

        old_files = [dict(row) for row in cursor.fetchall()]
        archived_count = 0
        archived_bytes = 0
        errors = []

        for file_info in old_files:
            try:
                source_path = Path(file_info['file_path'])

                if not source_path.exists():
                    logger.warning(f"File not found for archiving: {source_path}")
                    continue

                # Generate archive path
                archive_path = config.ARCHIVE_DIR / source_path.name

                if not dry_run:
                    # Move to archive
                    shutil.move(str(source_path), str(archive_path))

                    # Update database
                    with self.db.transaction():
                        self.db.connection.execute(
                            "UPDATE files SET file_path = ? WHERE id = ?",
                            (str(archive_path.absolute()), file_info['id'])
                        )

                    archived_count += 1

                archived_bytes += file_info['size_bytes']

            except Exception as e:
                errors.append({
                    'file_id': file_info['id'],
                    'error': str(e)
                })
                logger.error(f"Failed to archive file {file_info['id']}: {e}")

        results = {
            'found': len(old_files),
            'archived': archived_count,
            'archived_bytes': archived_bytes,
            'archived_formatted': config.format_file_size(archived_bytes),
            'errors': errors,
            'dry_run': dry_run
        }

        logger.info(
            f"File archiving: {archived_count}/{len(old_files)} archived, "
            f"{config.format_file_size(archived_bytes)} moved"
        )

        return results

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage usage statistics.

        Returns:
            Dictionary with storage statistics
        """
        cursor = self.db.connection.execute(
            """
            SELECT
                COUNT(*) as total_files,
                SUM(size_bytes) as total_size,
                AVG(size_bytes) as avg_size,
                MIN(size_bytes) as min_size,
                MAX(size_bytes) as max_size,
                COUNT(DISTINCT format) as unique_formats
            FROM files
            """
        )
        stats = dict(cursor.fetchone())

        # Format breakdown
        cursor = self.db.connection.execute(
            """
            SELECT format, COUNT(*) as count, SUM(size_bytes) as total_size
            FROM files
            GROUP BY format
            ORDER BY total_size DESC
            """
        )
        format_stats = [dict(row) for row in cursor.fetchall()]

        # Calculate percentages
        total_size = stats['total_size'] or 0

        return {
            'total_files': stats['total_files'],
            'total_size_bytes': total_size,
            'total_size_formatted': config.format_file_size(total_size),
            'avg_size_bytes': stats['avg_size'],
            'avg_size_formatted': config.format_file_size(stats['avg_size'] or 0),
            'min_size_bytes': stats['min_size'],
            'max_size_bytes': stats['max_size'],
            'unique_formats': stats['unique_formats'],
            'format_breakdown': format_stats,
            'quota_max_bytes': config.STORAGE_QUOTA_MAX,
            'quota_max_formatted': config.format_file_size(config.STORAGE_QUOTA_MAX),
            'quota_used_percentage': config.calculate_storage_percentage(total_size),
            'quota_available_bytes': config.STORAGE_QUOTA_MAX - total_size,
            'quota_available_formatted': config.format_file_size(
                max(0, config.STORAGE_QUOTA_MAX - total_size)
            ),
            'is_warning': config.is_storage_warning(total_size),
            'is_critical': config.is_storage_critical(total_size)
        }

    def verify_file_integrity(self, file_id: int) -> bool:
        """
        Verify file integrity by recalculating hash.

        Args:
            file_id: File database ID

        Returns:
            True if hash matches

        Raises:
            FileManagerError: If verification fails
        """
        file_info = self.get_file(file_id)
        if not file_info:
            raise FileManagerError(f"File not found: {file_id}")

        file_path = Path(file_info['file_path'])
        if not file_path.exists():
            raise FileManagerError(f"Physical file not found: {file_path}")

        current_hash = self.calculate_hash(file_path)
        stored_hash = file_info['file_hash']

        if current_hash != stored_hash:
            logger.error(
                f"File integrity check failed: {file_id} "
                f"(expected {stored_hash[:8]}..., got {current_hash[:8]}...)"
            )
            return False

        logger.info(f"File integrity verified: {file_id}")
        return True

    def get_duplicate_files(self) -> List[Dict[str, Any]]:
        """
        Find all files with duplicate hashes.

        Returns:
            List of file groups with same hash
        """
        cursor = self.db.connection.execute(
            """
            SELECT file_hash, COUNT(*) as count
            FROM files
            GROUP BY file_hash
            HAVING count > 1
            """
        )

        duplicates = []
        for row in cursor.fetchall():
            hash_val = row['file_hash']

            # Get all files with this hash
            files_cursor = self.db.connection.execute(
                "SELECT * FROM files WHERE file_hash = ?",
                (hash_val,)
            )
            files = [dict(f) for f in files_cursor.fetchall()]

            duplicates.append({
                'file_hash': hash_val,
                'count': row['count'],
                'files': files
            })

        return duplicates

    def close(self):
        """Close file manager and release resources."""
        logger.debug("FileManager closed")


# ============================================================================
# Context Manager Support
# ============================================================================

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'FileManager',
    'FileManagerError',
    'FileNotFoundError',
    'FileSizeError',
    'FileFormatError',
    'StorageQuotaError',
    'DuplicateFileError'
]
