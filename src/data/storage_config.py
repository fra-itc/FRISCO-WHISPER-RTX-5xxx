#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Storage Configuration
Centralized configuration for file storage and management
"""

from pathlib import Path
from typing import List, Dict, Any

# ============================================================================
# Storage Paths
# ============================================================================

# Base directory for all uploads
UPLOAD_BASE_DIR = Path("audio/uploads")

# Archive directory for old files
ARCHIVE_DIR = Path("audio/archive")

# Temporary directory for processing
TEMP_DIR = Path("audio/temp")


# ============================================================================
# File Size Limits
# ============================================================================

# Maximum file size in bytes (500 MB)
MAX_FILE_SIZE = 500 * 1024 * 1024

# Minimum file size in bytes (1 KB)
MIN_FILE_SIZE = 1024

# Warning threshold for large files (100 MB)
LARGE_FILE_WARNING = 100 * 1024 * 1024


# ============================================================================
# Supported Audio Formats
# ============================================================================

# Supported audio formats with MIME types
SUPPORTED_FORMATS: Dict[str, List[str]] = {
    'wav': ['audio/wav', 'audio/x-wav', 'audio/wave'],
    'mp3': ['audio/mpeg', 'audio/mp3'],
    'm4a': ['audio/mp4', 'audio/x-m4a'],
    'mp4': ['audio/mp4', 'video/mp4'],
    'aac': ['audio/aac', 'audio/x-aac'],
    'flac': ['audio/flac', 'audio/x-flac'],
    'opus': ['audio/opus', 'audio/ogg'],
    'waptt.opus': ['audio/opus', 'audio/ogg'],  # WhatsApp audio
    'ogg': ['audio/ogg'],
    'wma': ['audio/x-ms-wma'],
    'webm': ['audio/webm']
}

# List of all supported extensions
ALLOWED_EXTENSIONS = list(SUPPORTED_FORMATS.keys())


# ============================================================================
# Storage Quotas
# ============================================================================

# Maximum total storage in bytes (50 GB)
STORAGE_QUOTA_MAX = 50 * 1024 * 1024 * 1024

# Warning threshold for storage usage (80%)
STORAGE_WARNING_THRESHOLD = 0.8

# Critical threshold for storage usage (95%)
STORAGE_CRITICAL_THRESHOLD = 0.95


# ============================================================================
# Archive Settings
# ============================================================================

# Default days to keep files before archiving
DEFAULT_ARCHIVE_DAYS = 90

# Days to keep archived files before deletion
ARCHIVE_RETENTION_DAYS = 180

# Automatically archive orphaned files (no associated jobs)
AUTO_ARCHIVE_ORPHANED = True

# Days before orphaned files are archived
ORPHANED_FILE_ARCHIVE_DAYS = 30


# ============================================================================
# File Organization
# ============================================================================

# Storage structure pattern: {base_dir}/{year}/{month}/{hash}.{ext}
USE_DATE_ORGANIZATION = True

# Use file hash as filename (recommended for deduplication)
USE_HASH_AS_FILENAME = True

# Preserve original filenames (creates symlinks)
PRESERVE_ORIGINAL_NAMES = False


# ============================================================================
# Cleanup Settings
# ============================================================================

# Enable automatic cleanup of orphaned files
ENABLE_AUTO_CLEANUP = True

# Minimum age in days before a file can be deleted
MIN_DELETE_AGE_DAYS = 7

# Maximum number of files to process in one cleanup operation
CLEANUP_BATCH_SIZE = 100


# ============================================================================
# Validation Settings
# ============================================================================

# Verify file integrity after upload
VERIFY_UPLOAD_HASH = True

# Check for duplicate files before upload
CHECK_DUPLICATES = True

# Reject files with invalid audio headers
VALIDATE_AUDIO_HEADERS = True


# ============================================================================
# Performance Settings
# ============================================================================

# Buffer size for file operations (4 MB)
FILE_BUFFER_SIZE = 4 * 1024 * 1024

# Hash calculation chunk size (64 KB)
HASH_CHUNK_SIZE = 64 * 1024

# Maximum concurrent file operations
MAX_CONCURRENT_OPS = 5


# ============================================================================
# Helper Functions
# ============================================================================

def get_upload_path(year: int, month: int, filename: str) -> Path:
    """
    Generate organized upload path.

    Args:
        year: Year (YYYY)
        month: Month (1-12)
        filename: Filename with extension

    Returns:
        Path object for file storage
    """
    if USE_DATE_ORGANIZATION:
        return UPLOAD_BASE_DIR / str(year) / f"{month:02d}" / filename
    return UPLOAD_BASE_DIR / filename


def is_format_supported(extension: str) -> bool:
    """
    Check if file format is supported.

    Args:
        extension: File extension (with or without dot)

    Returns:
        True if format is supported
    """
    ext = extension.lstrip('.').lower()
    return ext in ALLOWED_EXTENSIONS


def get_mime_types(extension: str) -> List[str]:
    """
    Get MIME types for file extension.

    Args:
        extension: File extension (with or without dot)

    Returns:
        List of valid MIME types
    """
    ext = extension.lstrip('.').lower()
    return SUPPORTED_FORMATS.get(ext, [])


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def calculate_storage_percentage(used_bytes: int) -> float:
    """
    Calculate storage usage percentage.

    Args:
        used_bytes: Bytes currently used

    Returns:
        Percentage of quota used (0-100)
    """
    return (used_bytes / STORAGE_QUOTA_MAX) * 100


def is_storage_warning(used_bytes: int) -> bool:
    """
    Check if storage is at warning level.

    Args:
        used_bytes: Bytes currently used

    Returns:
        True if warning threshold exceeded
    """
    return used_bytes >= (STORAGE_QUOTA_MAX * STORAGE_WARNING_THRESHOLD)


def is_storage_critical(used_bytes: int) -> bool:
    """
    Check if storage is at critical level.

    Args:
        used_bytes: Bytes currently used

    Returns:
        True if critical threshold exceeded
    """
    return used_bytes >= (STORAGE_QUOTA_MAX * STORAGE_CRITICAL_THRESHOLD)


# ============================================================================
# Configuration Validation
# ============================================================================

def validate_config() -> Dict[str, Any]:
    """
    Validate storage configuration.

    Returns:
        Dictionary with validation results
    """
    issues = []
    warnings = []

    # Check directory paths
    if not UPLOAD_BASE_DIR.name:
        issues.append("UPLOAD_BASE_DIR must be specified")

    # Check size limits
    if MAX_FILE_SIZE <= 0:
        issues.append("MAX_FILE_SIZE must be positive")

    if MIN_FILE_SIZE >= MAX_FILE_SIZE:
        issues.append("MIN_FILE_SIZE must be less than MAX_FILE_SIZE")

    # Check quota
    if STORAGE_QUOTA_MAX <= 0:
        issues.append("STORAGE_QUOTA_MAX must be positive")

    if STORAGE_WARNING_THRESHOLD >= STORAGE_CRITICAL_THRESHOLD:
        warnings.append("STORAGE_WARNING_THRESHOLD should be less than STORAGE_CRITICAL_THRESHOLD")

    # Check archive settings
    if DEFAULT_ARCHIVE_DAYS < 0:
        issues.append("DEFAULT_ARCHIVE_DAYS cannot be negative")

    if ARCHIVE_RETENTION_DAYS < DEFAULT_ARCHIVE_DAYS:
        warnings.append("ARCHIVE_RETENTION_DAYS should be >= DEFAULT_ARCHIVE_DAYS")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }


# Validate on import
_validation = validate_config()
if not _validation['valid']:
    raise ValueError(f"Invalid storage configuration: {_validation['issues']}")
if _validation['warnings']:
    import warnings
    for warning in _validation['warnings']:
        warnings.warn(f"Storage config warning: {warning}")


# ============================================================================
# Export Configuration
# ============================================================================

__all__ = [
    # Paths
    'UPLOAD_BASE_DIR',
    'ARCHIVE_DIR',
    'TEMP_DIR',

    # Size limits
    'MAX_FILE_SIZE',
    'MIN_FILE_SIZE',
    'LARGE_FILE_WARNING',

    # Formats
    'SUPPORTED_FORMATS',
    'ALLOWED_EXTENSIONS',

    # Quotas
    'STORAGE_QUOTA_MAX',
    'STORAGE_WARNING_THRESHOLD',
    'STORAGE_CRITICAL_THRESHOLD',

    # Archive settings
    'DEFAULT_ARCHIVE_DAYS',
    'ARCHIVE_RETENTION_DAYS',
    'AUTO_ARCHIVE_ORPHANED',
    'ORPHANED_FILE_ARCHIVE_DAYS',

    # Organization
    'USE_DATE_ORGANIZATION',
    'USE_HASH_AS_FILENAME',
    'PRESERVE_ORIGINAL_NAMES',

    # Cleanup
    'ENABLE_AUTO_CLEANUP',
    'MIN_DELETE_AGE_DAYS',
    'CLEANUP_BATCH_SIZE',

    # Validation
    'VERIFY_UPLOAD_HASH',
    'CHECK_DUPLICATES',
    'VALIDATE_AUDIO_HEADERS',

    # Performance
    'FILE_BUFFER_SIZE',
    'HASH_CHUNK_SIZE',
    'MAX_CONCURRENT_OPS',

    # Helper functions
    'get_upload_path',
    'is_format_supported',
    'get_mime_types',
    'format_file_size',
    'calculate_storage_percentage',
    'is_storage_warning',
    'is_storage_critical',
    'validate_config'
]
