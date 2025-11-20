#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick verification script for database setup
Tests basic functionality of the data layer
"""

import sys
import io
from pathlib import Path
import tempfile
import shutil

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data import DatabaseManager, DatabaseError


def test_database_setup():
    """Quick test of database functionality"""
    print("\n" + "="*70)
    print("  FRISCO WHISPER RTX 5xxx - Database Setup Verification")
    print("="*70 + "\n")

    # Create temporary directory for test
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / 'test.db'

    try:
        # Test 1: Initialize database
        print("[1/5] Testing database initialization...")
        db = DatabaseManager(str(db_path))
        print("✓ Database initialized successfully")

        # Test 2: Check schema
        print("\n[2/5] Testing schema creation...")
        cursor = db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row['name'] for row in cursor.fetchall()}
        expected_tables = {'files', 'transcription_jobs', 'transcriptions', 'schema_metadata'}

        if expected_tables.issubset(tables):
            print(f"✓ All required tables created: {', '.join(expected_tables)}")
        else:
            print(f"✗ Missing tables: {expected_tables - tables}")
            return False

        # Test 3: Create test audio file
        print("\n[3/5] Testing file operations...")
        audio_dir = temp_dir / 'audio'
        audio_dir.mkdir()
        test_file = audio_dir / 'test.m4a'
        test_file.write_text('fake audio content for testing')

        file_id, is_new = db.add_or_get_file(str(test_file))
        print(f"✓ File added: ID={file_id}, is_new={is_new}")

        # Test 4: Create and manage job
        print("\n[4/5] Testing job creation and updates...")
        job_id = db.create_job(
            file_path=str(test_file),
            model_size='medium',
            task_type='transcribe',
            language='en'
        )
        print(f"✓ Job created: {job_id}")

        db.update_job(job_id, status='completed')
        job = db.get_job(job_id)
        if job and job['status'] == 'completed':
            print(f"✓ Job updated successfully")
        else:
            print("✗ Job update failed")
            return False

        # Test 5: Save transcription
        print("\n[5/5] Testing transcription save...")
        segments = [
            {'id': 1, 'start': 0.0, 'end': 2.5, 'text': 'Test transcription'},
        ]

        transcription_id = db.save_transcription(
            job_id=job_id,
            text='Test transcription',
            language='en',
            segments=segments
        )
        print(f"✓ Transcription saved: ID={transcription_id}")

        # Get statistics
        print("\n" + "="*70)
        print("Database Statistics:")
        print("="*70)
        stats = db.get_statistics()
        print(f"  Total Jobs: {stats['total_jobs']}")
        print(f"  Completed Jobs: {stats['completed_jobs']}")
        print(f"  Unique Files: {stats['unique_files']}")

        db.close()

        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - Database setup is working correctly!")
        print("="*70 + "\n")

        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    success = test_database_setup()
    sys.exit(0 if success else 1)
