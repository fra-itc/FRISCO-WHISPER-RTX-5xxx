"""
Unit tests for database operations.

Tests database schema creation, CRUD operations, and data integrity
for the transcription tracking database.
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Tests for database connection and schema
# ============================================================================

class TestDatabaseSchema:
    """Test suite for database schema operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_database_creation(self, temp_db):
        """Test that database file is created."""
        assert temp_db.exists()
        assert temp_db.is_file()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_transcriptions_table_exists(self, temp_db):
        """Test that transcriptions table exists."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='transcriptions'
        """)

        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == 'transcriptions'

    @pytest.mark.unit
    @pytest.mark.fast
    def test_transcriptions_table_schema(self, temp_db):
        """Test that transcriptions table has correct columns."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = cursor.fetchall()
        conn.close()

        column_names = [col[1] for col in columns]

        # Check for expected columns
        expected_columns = [
            'id', 'filename', 'original_path', 'transcript_path',
            'language', 'model_size', 'compute_type', 'duration_seconds',
            'processing_time', 'status', 'error_message',
            'created_at', 'completed_at'
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in table"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_primary_key_exists(self, temp_db):
        """Test that id column is primary key."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = cursor.fetchall()
        conn.close()

        # Find id column and check if it's primary key
        id_column = [col for col in columns if col[1] == 'id'][0]
        assert id_column[5] == 1, "id should be primary key"


# ============================================================================
# Tests for INSERT operations
# ============================================================================

class TestDatabaseInsert:
    """Test suite for database INSERT operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_insert_transcription_record(self, temp_db):
        """Test inserting a new transcription record."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transcriptions
            (filename, original_path, language, model_size, compute_type, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'en', 'medium', 'float16', 'pending'))

        conn.commit()
        inserted_id = cursor.lastrowid
        conn.close()

        assert inserted_id > 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_insert_multiple_records(self, temp_db):
        """Test inserting multiple transcription records."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        records = [
            ('file1.wav', '/path/to/file1.wav', 'en', 'small', 'float16', 'pending'),
            ('file2.wav', '/path/to/file2.wav', 'es', 'medium', 'float32', 'pending'),
            ('file3.wav', '/path/to/file3.wav', 'fr', 'large-v3', 'int8', 'pending'),
        ]

        for record in records:
            cursor.execute("""
                INSERT INTO transcriptions
                (filename, original_path, language, model_size, compute_type, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, record)

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM transcriptions")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_insert_with_default_timestamp(self, temp_db):
        """Test that created_at timestamp is automatically set."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transcriptions
            (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'pending'))

        conn.commit()

        cursor.execute("SELECT created_at FROM transcriptions WHERE filename = ?", ('test.wav',))
        created_at = cursor.fetchone()[0]
        conn.close()

        assert created_at is not None
        # Verify it's a valid timestamp format
        assert len(created_at) > 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_insert_with_nullable_fields(self, temp_db):
        """Test inserting record with NULL values in nullable fields."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transcriptions
            (filename, original_path, status, transcript_path, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'pending', None, None))

        conn.commit()

        cursor.execute("SELECT transcript_path, error_message FROM transcriptions WHERE filename = ?",
                       ('test.wav',))
        result = cursor.fetchone()
        conn.close()

        assert result[0] is None  # transcript_path
        assert result[1] is None  # error_message


# ============================================================================
# Tests for SELECT operations
# ============================================================================

class TestDatabaseSelect:
    """Test suite for database SELECT operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_select_all_records(self, temp_db):
        """Test selecting all transcription records."""
        # Insert test data
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transcriptions
            (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'pending'))

        conn.commit()

        # Select all records
        cursor.execute("SELECT * FROM transcriptions")
        records = cursor.fetchall()
        conn.close()

        assert len(records) > 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_select_by_status(self, temp_db):
        """Test selecting records by status."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert records with different statuses
        cursor.execute("""
            INSERT INTO transcriptions (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test1.wav', '/path/to/test1.wav', 'pending'))

        cursor.execute("""
            INSERT INTO transcriptions (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test2.wav', '/path/to/test2.wav', 'completed'))

        conn.commit()

        # Select only pending records
        cursor.execute("SELECT * FROM transcriptions WHERE status = ?", ('pending',))
        pending = cursor.fetchall()

        cursor.execute("SELECT * FROM transcriptions WHERE status = ?", ('completed',))
        completed = cursor.fetchall()
        conn.close()

        assert len(pending) == 1
        assert len(completed) == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_select_by_language(self, temp_db):
        """Test selecting records by language."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert records with different languages
        for lang in ['en', 'es', 'fr', 'en']:
            cursor.execute("""
                INSERT INTO transcriptions (filename, original_path, language, status)
                VALUES (?, ?, ?, ?)
            """, (f'test_{lang}.wav', f'/path/{lang}.wav', lang, 'pending'))

        conn.commit()

        cursor.execute("SELECT * FROM transcriptions WHERE language = ?", ('en',))
        en_records = cursor.fetchall()
        conn.close()

        assert len(en_records) == 2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_select_order_by_created_at(self, temp_db):
        """Test selecting records ordered by creation time."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert multiple records
        for i in range(3):
            cursor.execute("""
                INSERT INTO transcriptions (filename, original_path, status)
                VALUES (?, ?, ?)
            """, (f'test{i}.wav', f'/path/test{i}.wav', 'pending'))

        conn.commit()

        cursor.execute("SELECT filename FROM transcriptions ORDER BY created_at ASC")
        records = cursor.fetchall()
        conn.close()

        assert len(records) == 3
        # First record should be test0.wav
        assert records[0][0] == 'test0.wav'


# ============================================================================
# Tests for UPDATE operations
# ============================================================================

class TestDatabaseUpdate:
    """Test suite for database UPDATE operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_status(self, temp_db):
        """Test updating transcription status."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert a record
        cursor.execute("""
            INSERT INTO transcriptions (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'pending'))

        conn.commit()

        # Update status
        cursor.execute("""
            UPDATE transcriptions
            SET status = ?
            WHERE filename = ?
        """, ('completed', 'test.wav'))

        conn.commit()

        # Verify update
        cursor.execute("SELECT status FROM transcriptions WHERE filename = ?", ('test.wav',))
        status = cursor.fetchone()[0]
        conn.close()

        assert status == 'completed'

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_transcript_path(self, temp_db):
        """Test updating transcript path after completion."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transcriptions (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'pending'))

        conn.commit()

        # Update with transcript path
        cursor.execute("""
            UPDATE transcriptions
            SET transcript_path = ?, status = ?
            WHERE filename = ?
        """, ('/path/to/transcript.srt', 'completed', 'test.wav'))

        conn.commit()

        cursor.execute("SELECT transcript_path FROM transcriptions WHERE filename = ?", ('test.wav',))
        transcript_path = cursor.fetchone()[0]
        conn.close()

        assert transcript_path == '/path/to/transcript.srt'

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_processing_metrics(self, temp_db):
        """Test updating processing time and duration."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transcriptions (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'processing'))

        conn.commit()

        # Update with metrics
        cursor.execute("""
            UPDATE transcriptions
            SET duration_seconds = ?, processing_time = ?, status = ?
            WHERE filename = ?
        """, (120.5, 45.2, 'completed', 'test.wav'))

        conn.commit()

        cursor.execute("""
            SELECT duration_seconds, processing_time
            FROM transcriptions WHERE filename = ?
        """, ('test.wav',))

        result = cursor.fetchone()
        conn.close()

        assert result[0] == 120.5
        assert result[1] == 45.2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_error_message(self, temp_db):
        """Test updating error message on failure."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transcriptions (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'processing'))

        conn.commit()

        # Update with error
        cursor.execute("""
            UPDATE transcriptions
            SET status = ?, error_message = ?
            WHERE filename = ?
        """, ('failed', 'GPU out of memory', 'test.wav'))

        conn.commit()

        cursor.execute("""
            SELECT status, error_message
            FROM transcriptions WHERE filename = ?
        """, ('test.wav',))

        result = cursor.fetchone()
        conn.close()

        assert result[0] == 'failed'
        assert result[1] == 'GPU out of memory'


# ============================================================================
# Tests for DELETE operations
# ============================================================================

class TestDatabaseDelete:
    """Test suite for database DELETE operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_delete_record(self, temp_db):
        """Test deleting a transcription record."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transcriptions (filename, original_path, status)
            VALUES (?, ?, ?)
        """, ('test.wav', '/path/to/test.wav', 'pending'))

        conn.commit()

        # Delete the record
        cursor.execute("DELETE FROM transcriptions WHERE filename = ?", ('test.wav',))
        conn.commit()

        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM transcriptions WHERE filename = ?", ('test.wav',))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_delete_by_status(self, temp_db):
        """Test deleting records by status."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert multiple records
        for i in range(3):
            cursor.execute("""
                INSERT INTO transcriptions (filename, original_path, status)
                VALUES (?, ?, ?)
            """, (f'test{i}.wav', f'/path/test{i}.wav', 'failed' if i == 2 else 'completed'))

        conn.commit()

        # Delete failed records
        cursor.execute("DELETE FROM transcriptions WHERE status = ?", ('failed',))
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM transcriptions")
        total_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transcriptions WHERE status = ?", ('failed',))
        failed_count = cursor.fetchone()[0]
        conn.close()

        assert total_count == 2
        assert failed_count == 0


# ============================================================================
# Tests for complex queries
# ============================================================================

class TestDatabaseComplexQueries:
    """Test suite for complex database queries."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_count_by_status(self, temp_db):
        """Test counting records grouped by status."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert records with various statuses
        statuses = ['pending', 'processing', 'completed', 'failed', 'completed']
        for i, status in enumerate(statuses):
            cursor.execute("""
                INSERT INTO transcriptions (filename, original_path, status)
                VALUES (?, ?, ?)
            """, (f'test{i}.wav', f'/path/test{i}.wav', status))

        conn.commit()

        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM transcriptions
            GROUP BY status
        """)

        results = cursor.fetchall()
        conn.close()

        status_counts = {row[0]: row[1] for row in results}

        assert status_counts['completed'] == 2
        assert status_counts['pending'] == 1
        assert status_counts['failed'] == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_average_processing_time(self, temp_db):
        """Test calculating average processing time."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert records with processing times
        processing_times = [10.5, 20.3, 15.7]
        for i, pt in enumerate(processing_times):
            cursor.execute("""
                INSERT INTO transcriptions
                (filename, original_path, processing_time, status)
                VALUES (?, ?, ?, ?)
            """, (f'test{i}.wav', f'/path/test{i}.wav', pt, 'completed'))

        conn.commit()

        cursor.execute("""
            SELECT AVG(processing_time) as avg_time
            FROM transcriptions
            WHERE status = ?
        """, ('completed',))

        avg_time = cursor.fetchone()[0]
        conn.close()

        expected_avg = sum(processing_times) / len(processing_times)
        assert abs(avg_time - expected_avg) < 0.01

    @pytest.mark.unit
    @pytest.mark.fast
    def test_total_duration_by_language(self, temp_db):
        """Test summing audio duration by language."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert records
        records = [
            ('file1.wav', 'en', 60.0),
            ('file2.wav', 'en', 90.0),
            ('file3.wav', 'es', 45.0),
        ]

        for filename, lang, duration in records:
            cursor.execute("""
                INSERT INTO transcriptions
                (filename, original_path, language, duration_seconds, status)
                VALUES (?, ?, ?, ?, ?)
            """, (filename, f'/path/{filename}', lang, duration, 'completed'))

        conn.commit()

        cursor.execute("""
            SELECT language, SUM(duration_seconds) as total_duration
            FROM transcriptions
            GROUP BY language
        """)

        results = cursor.fetchall()
        conn.close()

        lang_durations = {row[0]: row[1] for row in results}

        assert lang_durations['en'] == 150.0
        assert lang_durations['es'] == 45.0


# ============================================================================
# Tests for data integrity
# ============================================================================

class TestDatabaseIntegrity:
    """Test suite for database data integrity."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_unique_id_constraint(self, temp_db):
        """Test that id is unique and auto-incrementing."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert multiple records
        ids = []
        for i in range(3):
            cursor.execute("""
                INSERT INTO transcriptions (filename, original_path, status)
                VALUES (?, ?, ?)
            """, (f'test{i}.wav', f'/path/test{i}.wav', 'pending'))
            ids.append(cursor.lastrowid)

        conn.commit()
        conn.close()

        # All IDs should be unique and sequential
        assert len(ids) == len(set(ids))
        assert ids == sorted(ids)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_not_null_constraints(self, temp_db):
        """Test that NOT NULL constraints are enforced."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Try to insert without required fields
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO transcriptions (transcript_path)
                VALUES (?)
            """, ('/path/to/transcript.srt',))

        conn.close()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_transaction_rollback(self, temp_db):
        """Test transaction rollback on error."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO transcriptions (filename, original_path, status)
                VALUES (?, ?, ?)
            """, ('test.wav', '/path/to/test.wav', 'pending'))

            # This should cause an error (missing required field in next insert)
            cursor.execute("""
                INSERT INTO transcriptions (transcript_path)
                VALUES (?)
            """, ('/path/to/transcript.srt',))

            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()

        cursor.execute("SELECT COUNT(*) FROM transcriptions")
        count = cursor.fetchone()[0]
        conn.close()

        # No records should exist after rollback
        assert count == 0
