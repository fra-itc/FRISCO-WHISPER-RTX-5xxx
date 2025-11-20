#!/usr/bin/env python3
"""
Example usage of FileManager for file upload, deduplication, and storage management.

This script demonstrates:
- File upload with automatic deduplication
- File metadata retrieval
- Storage quota checking
- File listing and filtering
- Cleanup of orphaned files
- Storage statistics
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import DatabaseManager, FileManager, storage_config


def main():
    """Demonstrate FileManager functionality."""

    # ========================================================================
    # 1. Initialize Database and FileManager
    # ========================================================================

    print("=" * 80)
    print("FRISCO WHISPER - File Manager Example")
    print("=" * 80)
    print()

    # Initialize database
    db = DatabaseManager('database/transcription.db')
    print(f"Database initialized: {db.db_path}")

    # Initialize file manager
    fm = FileManager(db)
    print(f"File manager initialized: {fm.base_dir}")
    print()

    # ========================================================================
    # 2. Upload Files with Deduplication
    # ========================================================================

    print("-" * 80)
    print("UPLOADING FILES")
    print("-" * 80)

    # Example audio file path
    audio_file = "audio/wedo.m4a"

    if Path(audio_file).exists():
        # First upload
        print(f"\n1. Uploading file: {audio_file}")
        file_id1, is_new1 = fm.upload_file(audio_file)
        print(f"   Result: file_id={file_id1}, is_new={is_new1}")

        # Second upload (should detect duplicate)
        print(f"\n2. Uploading same file again (testing deduplication)")
        file_id2, is_new2 = fm.upload_file(audio_file)
        print(f"   Result: file_id={file_id2}, is_new={is_new2}")
        print(f"   Deduplication worked: {file_id1 == file_id2 and not is_new2}")

        # Upload with custom name
        print(f"\n3. Uploading with custom original name")
        file_id3, is_new3 = fm.upload_file(
            audio_file,
            original_name="my_custom_audio.m4a"
        )
        print(f"   Result: file_id={file_id3}, is_new={is_new3}")
    else:
        print(f"Sample file not found: {audio_file}")
        print("Skipping upload examples...")

    print()

    # ========================================================================
    # 3. File Retrieval and Metadata
    # ========================================================================

    print("-" * 80)
    print("FILE RETRIEVAL")
    print("-" * 80)

    # Get recent files
    files = fm.list_files(limit=5)

    if files:
        print(f"\nRecent files (showing {len(files)}):")
        for i, file_info in enumerate(files, 1):
            print(f"\n{i}. File ID: {file_info['id']}")
            print(f"   Name: {file_info['original_name']}")
            print(f"   Format: {file_info['format']}")
            print(f"   Size: {storage_config.format_file_size(file_info['size_bytes'])}")
            print(f"   Hash: {file_info['file_hash'][:16]}...")
            print(f"   Uploaded: {file_info['uploaded_at']}")

        # Get file by ID
        print(f"\nRetrieving file by ID: {files[0]['id']}")
        file_info = fm.get_file(files[0]['id'])
        print(f"   Path: {file_info['file_path']}")

        # Get file by hash
        print(f"\nRetrieving file by hash: {files[0]['file_hash'][:16]}...")
        file_by_hash = fm.get_file_by_hash(files[0]['file_hash'])
        print(f"   Found: {file_by_hash is not None}")

    else:
        print("\nNo files found in database.")

    print()

    # ========================================================================
    # 4. Storage Statistics
    # ========================================================================

    print("-" * 80)
    print("STORAGE STATISTICS")
    print("-" * 80)

    stats = fm.get_storage_stats()

    print(f"\nTotal Files: {stats['total_files']}")
    print(f"Total Size: {stats['total_size_formatted']}")
    print(f"Average Size: {stats['avg_size_formatted']}")
    print(f"Unique Formats: {stats['unique_formats']}")

    print(f"\nStorage Quota:")
    print(f"  Used: {stats['total_size_formatted']}")
    print(f"  Max: {stats['quota_max_formatted']}")
    print(f"  Percentage: {stats['quota_used_percentage']:.2f}%")
    print(f"  Available: {stats['quota_available_formatted']}")

    if stats['is_critical']:
        print(f"  WARNING: Storage is CRITICAL!")
    elif stats['is_warning']:
        print(f"  WARNING: Storage is above warning threshold")

    if stats['format_breakdown']:
        print(f"\nFormat Breakdown:")
        for fmt_stats in stats['format_breakdown']:
            size_formatted = storage_config.format_file_size(fmt_stats['total_size'])
            print(f"  {fmt_stats['format']:10s}: {fmt_stats['count']:4d} files, {size_formatted}")

    print()

    # ========================================================================
    # 5. File Listing with Filters
    # ========================================================================

    print("-" * 80)
    print("FILE LISTING WITH FILTERS")
    print("-" * 80)

    # List by format
    print("\nFiles by format (MP3):")
    mp3_files = fm.list_files(format_filter='mp3', limit=5)
    print(f"  Found: {len(mp3_files)} MP3 files")

    print("\nFiles by format (M4A):")
    m4a_files = fm.list_files(format_filter='m4a', limit=5)
    print(f"  Found: {len(m4a_files)} M4A files")

    # Pagination example
    print("\nPagination example (first 3 files):")
    page1 = fm.list_files(limit=3, offset=0)
    for f in page1:
        print(f"  - {f['original_name']} ({storage_config.format_file_size(f['size_bytes'])})")

    print()

    # ========================================================================
    # 6. Reference Counting
    # ========================================================================

    print("-" * 80)
    print("REFERENCE COUNTING")
    print("-" * 80)

    if files:
        file_id = files[0]['id']
        ref_count = fm.count_file_references(file_id)

        print(f"\nFile ID {file_id}:")
        print(f"  Name: {files[0]['original_name']}")
        print(f"  Referenced by {ref_count} job(s)")

        if ref_count > 0:
            print(f"  ⚠ Cannot delete without force flag")
        else:
            print(f"  ✓ Can be safely deleted (no references)")

    print()

    # ========================================================================
    # 7. File Integrity Verification
    # ========================================================================

    print("-" * 80)
    print("FILE INTEGRITY VERIFICATION")
    print("-" * 80)

    if files:
        file_id = files[0]['id']
        print(f"\nVerifying integrity of file ID {file_id}...")

        try:
            is_valid = fm.verify_file_integrity(file_id)
            if is_valid:
                print(f"  ✓ File integrity verified successfully")
            else:
                print(f"  ✗ File integrity check FAILED")
        except Exception as e:
            print(f"  ✗ Error verifying integrity: {e}")

    print()

    # ========================================================================
    # 8. Cleanup Operations (Dry Run)
    # ========================================================================

    print("-" * 80)
    print("CLEANUP OPERATIONS (DRY RUN)")
    print("-" * 80)

    # Cleanup orphaned files
    print("\nCleaning up orphaned files (dry run)...")
    cleanup_result = fm.cleanup_orphaned_files(min_age_days=30, dry_run=True)

    print(f"  Found: {cleanup_result['found']} orphaned files")
    print(f"  Would delete: {cleanup_result['deleted']} files")
    print(f"  Would free: {cleanup_result['freed_formatted']}")
    print(f"  Errors: {len(cleanup_result['errors'])}")

    # Archive old files
    print("\nArchiving old files (dry run)...")
    archive_result = fm.archive_old_files(days=90, dry_run=True)

    print(f"  Found: {archive_result['found']} old files")
    print(f"  Would archive: {archive_result['archived']} files")
    print(f"  Would move: {archive_result['archived_formatted']}")
    print(f"  Errors: {len(archive_result['errors'])}")

    print()

    # ========================================================================
    # 9. Duplicate File Detection
    # ========================================================================

    print("-" * 80)
    print("DUPLICATE FILE DETECTION")
    print("-" * 80)

    duplicates = fm.get_duplicate_files()

    if duplicates:
        print(f"\nFound {len(duplicates)} sets of duplicate files:")
        for dup_group in duplicates:
            print(f"\n  Hash: {dup_group['file_hash'][:16]}...")
            print(f"  Count: {dup_group['count']} files")
            for f in dup_group['files']:
                print(f"    - ID {f['id']}: {f['original_name']}")
    else:
        print("\n✓ No duplicate files found")

    print()

    # ========================================================================
    # 10. Storage Configuration
    # ========================================================================

    print("-" * 80)
    print("STORAGE CONFIGURATION")
    print("-" * 80)

    print(f"\nSupported formats: {', '.join(storage_config.ALLOWED_EXTENSIONS)}")
    print(f"Max file size: {storage_config.format_file_size(storage_config.MAX_FILE_SIZE)}")
    print(f"Min file size: {storage_config.format_file_size(storage_config.MIN_FILE_SIZE)}")
    print(f"Storage quota: {storage_config.format_file_size(storage_config.STORAGE_QUOTA_MAX)}")
    print(f"Warning threshold: {storage_config.STORAGE_WARNING_THRESHOLD * 100:.0f}%")
    print(f"Critical threshold: {storage_config.STORAGE_CRITICAL_THRESHOLD * 100:.0f}%")

    print(f"\nArchive settings:")
    print(f"  Default archive age: {storage_config.DEFAULT_ARCHIVE_DAYS} days")
    print(f"  Archive retention: {storage_config.ARCHIVE_RETENTION_DAYS} days")
    print(f"  Orphaned file threshold: {storage_config.ORPHANED_FILE_ARCHIVE_DAYS} days")

    print(f"\nValidation:")
    print(f"  Verify upload hash: {storage_config.VERIFY_UPLOAD_HASH}")
    print(f"  Check duplicates: {storage_config.CHECK_DUPLICATES}")
    print(f"  Validate audio headers: {storage_config.VALIDATE_AUDIO_HEADERS}")

    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    print("-" * 80)
    print("CLEANUP")
    print("-" * 80)

    fm.close()
    db.close()

    print("\n✓ File manager and database closed successfully")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
