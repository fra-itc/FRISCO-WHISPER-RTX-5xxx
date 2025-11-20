"""
FRISCO WHISPER RTX 5xxx - Data Layer Module
Provides database management, file storage, transcript versioning, and format conversion
"""

from .database import (
    DatabaseManager,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseIntegrityError
)

from .file_manager import (
    FileManager,
    FileManagerError,
    FileNotFoundError,
    FileSizeError,
    FileFormatError,
    StorageQuotaError,
    DuplicateFileError
)

from .transcript_manager import (
    TranscriptManager,
    TranscriptError,
    TranscriptNotFoundError,
    VersionNotFoundError
)

from .format_converters import (
    FormatConverter,
    DiffGenerator
)

from . import storage_config

__all__ = [
    # Database
    'DatabaseManager',
    'DatabaseError',
    'DatabaseConnectionError',
    'DatabaseIntegrityError',

    # File Manager
    'FileManager',
    'FileManagerError',
    'FileNotFoundError',
    'FileSizeError',
    'FileFormatError',
    'StorageQuotaError',
    'DuplicateFileError',

    # Transcript Management
    'TranscriptManager',
    'TranscriptError',
    'TranscriptNotFoundError',
    'VersionNotFoundError',

    # Format Conversion
    'FormatConverter',
    'DiffGenerator',

    # Storage Config
    'storage_config'
]

__version__ = '1.2.0'
