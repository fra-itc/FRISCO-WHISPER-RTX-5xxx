#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Full Stack Integration Test
Tests complete workflow: upload → transcribe → version → export
"""

import pytest
import tempfile
import json
import shutil
from pathlib import Path
from datetime import datetime
import wave
import struct
import time

from src.data.database import DatabaseManager
from src.data.file_manager import FileManager
from src.data.transcript_manager import TranscriptManager
from src.data.format_converters import FormatConverter


@pytest.fixture(scope='module')
def test_environment():
    """
    Create isolated test environment with temporary database and file storage.
    """
    # Create temporary directory for test environment
    test_dir = Path(tempfile.mkdtemp(prefix='frisco_fullstack_test_'))

    # Setup paths
    db_path = test_dir / 'test.db'
    upload_dir = test_dir / 'uploads'
    transcripts_dir = test_dir / 'transcripts'

    upload_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    # Initialize components
    db_manager = DatabaseManager(str(db_path))
    file_manager = FileManager(db_manager, base_dir=upload_dir)
    transcript_manager = TranscriptManager(db_manager)

    env = {
        'test_dir': test_dir,
        'db_path': db_path,
        'upload_dir': upload_dir,
        'transcripts_dir': transcripts_dir,
        'db': db_manager,
        'file_mgr': file_manager,
        'transcript_mgr': transcript_manager
    }

    yield env

    # Cleanup
    db_manager.close()
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def sample_audio_file(test_environment):
    """
    Create a minimal valid WAV file for testing.
    """
    test_dir = test_environment['test_dir']
    audio_file = test_dir / 'test_audio.wav'

    # Create a simple WAV file (1 second, mono, 16kHz)
    sample_rate = 16000
    duration = 1  # seconds
    num_samples = sample_rate * duration

    with wave.open(str(audio_file), 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Generate simple sine wave
        for i in range(num_samples):
            # 440 Hz tone (A4)
            value = int(32767 * 0.1 * (i % 100) / 100)
            wav_file.writeframes(struct.pack('<h', value))

    return audio_file


@pytest.fixture
def sample_segments():
    """Create sample transcript segments."""
    return [
        {
            'start': 0.0,
            'end': 2.5,
            'text': 'This is the first segment.'
        },
        {
            'start': 2.5,
            'end': 5.0,
            'text': 'This is the second segment.'
        },
        {
            'start': 5.0,
            'end': 8.3,
            'text': 'This is the third and final segment.'
        }
    ]


class TestFullStackWorkflow:
    """Test complete end-to-end workflow."""

    def test_01_file_upload_and_deduplication(self, test_environment, sample_audio_file):
        """
        Test file upload with deduplication.
        """
        file_mgr = test_environment['file_mgr']
        db = test_environment['db']

        # Upload file first time
        file_id_1, is_new_1 = file_mgr.upload_file(str(sample_audio_file))

        assert is_new_1 is True, "First upload should be new"
        assert file_id_1 > 0, "File ID should be positive"

        # Verify file in database
        file_info = file_mgr.get_file(file_id_1)
        assert file_info is not None
        assert file_info['original_name'] == sample_audio_file.name
        assert file_info['format'] == 'wav'

        # Upload same file again (should detect duplicate)
        file_id_2, is_new_2 = file_mgr.upload_file(str(sample_audio_file))

        assert is_new_2 is False, "Second upload should be duplicate"
        assert file_id_2 == file_id_1, "Should return same file ID for duplicate"

        # Verify only one file record exists
        cursor = db.connection.execute("SELECT COUNT(*) as count FROM files")
        count = cursor.fetchone()['count']
        assert count == 1, "Should only have one file record"

    def test_02_job_creation(self, test_environment, sample_audio_file):
        """
        Test transcription job creation.
        """
        file_mgr = test_environment['file_mgr']
        db = test_environment['db']

        # Upload file
        file_id, _ = file_mgr.upload_file(str(sample_audio_file))

        # Create job
        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='small',
            task_type='transcribe',
            language='en',
            compute_type='float16',
            device='cuda',
            beam_size=5,
            duration_seconds=1.0
        )

        assert job_id is not None
        assert len(job_id) == 36  # UUID length

        # Verify job in database
        job = db.get_job(job_id)
        assert job is not None
        assert job['status'] == 'pending'
        assert job['model_size'] == 'small'
        assert job['task_type'] == 'transcribe'
        assert job['language'] == 'en'
        assert job['file_id'] == file_id

    def test_03_job_lifecycle(self, test_environment, sample_audio_file):
        """
        Test job status transitions.
        """
        db = test_environment['db']

        # Create job
        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        # Verify initial status
        job = db.get_job(job_id)
        assert job['status'] == 'pending'
        assert job['started_at'] is None
        assert job['completed_at'] is None

        # Update to processing
        started_at = datetime.now()
        success = db.update_job(
            job_id,
            status='processing',
            started_at=started_at
        )
        assert success is True

        job = db.get_job(job_id)
        assert job['status'] == 'processing'
        assert job['started_at'] is not None

        # Update to completed
        completed_at = datetime.now()
        success = db.update_job(
            job_id,
            status='completed',
            completed_at=completed_at,
            processing_time_seconds=2.5,
            detected_language='en',
            language_probability=0.98
        )
        assert success is True

        job = db.get_job(job_id)
        assert job['status'] == 'completed'
        assert job['completed_at'] is not None
        assert job['processing_time_seconds'] == 2.5
        assert job['detected_language'] == 'en'
        assert job['language_probability'] == 0.98

    def test_04_transcript_save_with_versioning(
        self,
        test_environment,
        sample_audio_file,
        sample_segments
    ):
        """
        Test transcript save with automatic version creation.
        """
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        # Create job
        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        # Save transcript
        full_text = ' '.join([seg['text'] for seg in sample_segments])
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=full_text,
            segments=sample_segments,
            language='en'
        )

        assert transcript_id > 0

        # Verify transcript
        transcript = transcript_mgr.get_transcript(transcript_id)
        assert transcript is not None
        assert transcript['job_id'] == job_id
        assert transcript['language'] == 'en'
        assert transcript['segment_count'] == len(sample_segments)
        assert transcript['version_number'] == 1
        assert transcript['is_current'] == 1

        # Verify initial version was created
        versions = transcript_mgr.get_versions(transcript_id)
        assert len(versions) == 1
        assert versions[0]['version_number'] == 1
        assert versions[0]['is_current'] == 1
        assert versions[0]['change_note'] == 'Initial transcription'

    def test_05_transcript_update_creates_version(
        self,
        test_environment,
        sample_audio_file,
        sample_segments
    ):
        """
        Test that updating transcript creates new version.
        """
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        # Create and save transcript
        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        full_text = ' '.join([seg['text'] for seg in sample_segments])
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=full_text,
            segments=sample_segments,
            language='en'
        )

        # Update transcript
        updated_segments = sample_segments.copy()
        updated_segments[0]['text'] = 'This is the UPDATED first segment.'
        updated_text = ' '.join([seg['text'] for seg in updated_segments])

        version_number = transcript_mgr.update_transcript(
            transcript_id=transcript_id,
            text=updated_text,
            segments=updated_segments,
            created_by='test_user',
            change_note='Fixed first segment'
        )

        assert version_number == 2

        # Verify versions
        versions = transcript_mgr.get_versions(transcript_id)
        assert len(versions) == 2

        # Version 2 should be current
        current_version = [v for v in versions if v['is_current'] == 1]
        assert len(current_version) == 1
        assert current_version[0]['version_number'] == 2
        assert current_version[0]['change_note'] == 'Fixed first segment'
        assert current_version[0]['created_by'] == 'test_user'

        # Version 1 should not be current
        old_version = [v for v in versions if v['is_current'] == 0]
        assert len(old_version) == 1
        assert old_version[0]['version_number'] == 1

        # Get current transcript should return version 2
        transcript = transcript_mgr.get_transcript(transcript_id)
        assert transcript['version_number'] == 2
        assert 'UPDATED' in transcript['text']

    def test_06_version_comparison(
        self,
        test_environment,
        sample_audio_file,
        sample_segments
    ):
        """
        Test version comparison functionality.
        """
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        # Create transcript with two versions
        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        # Version 1
        full_text = ' '.join([seg['text'] for seg in sample_segments])
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=full_text,
            segments=sample_segments,
            language='en'
        )

        # Version 2 (modified)
        updated_segments = sample_segments.copy()
        updated_segments[0]['text'] = 'Modified first segment.'
        updated_segments.append({
            'start': 8.3,
            'end': 10.0,
            'text': 'Added fourth segment.'
        })
        updated_text = ' '.join([seg['text'] for seg in updated_segments])

        transcript_mgr.update_transcript(
            transcript_id=transcript_id,
            text=updated_text,
            segments=updated_segments
        )

        # Compare versions
        comparison = transcript_mgr.compare_versions(
            transcript_id=transcript_id,
            version1=1,
            version2=2
        )

        assert comparison is not None
        assert comparison['version1']['number'] == 1
        assert comparison['version2']['number'] == 2

        # Text diff
        text_diff = comparison['text_diff']
        assert text_diff['old_word_count'] == 14  # Original word count
        assert text_diff['new_word_count'] > text_diff['old_word_count']  # Added words
        assert text_diff['word_diff'] > 0  # Positive diff

        # Segment diff
        segment_diff = comparison['segment_diff']
        assert segment_diff['old_segment_count'] == 3
        assert segment_diff['new_segment_count'] == 4
        assert segment_diff['segment_diff'] == 1  # Added 1 segment

    def test_07_version_rollback(
        self,
        test_environment,
        sample_audio_file,
        sample_segments
    ):
        """
        Test rollback to previous version.
        """
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        # Create transcript with multiple versions
        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        original_text = ' '.join([seg['text'] for seg in sample_segments])
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=original_text,
            segments=sample_segments,
            language='en'
        )

        # Create version 2
        updated_segments = sample_segments.copy()
        updated_segments[0]['text'] = 'BAD VERSION.'
        updated_text = ' '.join([seg['text'] for seg in updated_segments])

        transcript_mgr.update_transcript(
            transcript_id=transcript_id,
            text=updated_text,
            segments=updated_segments
        )

        # Verify version 2 is current
        current = transcript_mgr.get_transcript(transcript_id)
        assert current['version_number'] == 2
        assert 'BAD VERSION' in current['text']

        # Rollback to version 1
        new_version = transcript_mgr.rollback_to_version(
            transcript_id=transcript_id,
            version_number=1,
            created_by='test_user',
            change_note='Rollback to original'
        )

        assert new_version == 3  # Creates version 3

        # Verify version 3 has version 1 content
        current = transcript_mgr.get_transcript(transcript_id)
        assert current['version_number'] == 3
        assert 'BAD VERSION' not in current['text']
        assert current['text'] == original_text
        assert current['change_note'] == 'Rollback to original'

    def test_08_export_all_formats(
        self,
        test_environment,
        sample_audio_file,
        sample_segments
    ):
        """
        Test export to all supported formats.
        """
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']
        transcripts_dir = test_environment['transcripts_dir']

        # Create transcript
        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        full_text = ' '.join([seg['text'] for seg in sample_segments])
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=full_text,
            segments=sample_segments,
            language='en'
        )

        # Test all export formats
        formats = ['srt', 'vtt', 'json', 'txt', 'csv']

        for format_name in formats:
            output_path = transcripts_dir / f'test.{format_name}'

            content = transcript_mgr.export_transcript(
                transcript_id=transcript_id,
                format_name=format_name,
                output_path=str(output_path)
            )

            # Verify content returned
            assert content is not None
            assert len(content) > 0

            # Verify file created
            assert output_path.exists()
            assert output_path.stat().st_size > 0

            # Format-specific validation
            if format_name == 'srt':
                assert '00:00:00,000 --> 00:00:02,500' in content
                assert 'This is the first segment' in content

            elif format_name == 'vtt':
                assert 'WEBVTT' in content
                assert '00:00:00.000 --> 00:00:02.500' in content

            elif format_name == 'json':
                data = json.loads(content)
                assert data['format'] == 'whisper-json'
                assert len(data['segments']) == 3
                assert data['metadata']['language'] == 'en'

            elif format_name == 'txt':
                assert 'This is the first segment' in content
                assert 'This is the second segment' in content

            elif format_name == 'csv':
                assert 'index,start,end,duration,text' in content
                assert '0.000' in content

        # Verify export history
        history = transcript_mgr.get_version_history(transcript_id)
        assert history['export_count'] == len(formats)

    def test_09_full_text_search(
        self,
        test_environment,
        sample_audio_file,
        sample_segments
    ):
        """
        Test full-text search functionality.
        """
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        # Create multiple transcripts
        for i in range(3):
            job_id = db.create_job(
                file_path=str(sample_audio_file),
                model_size='base',
                task_type='transcribe'
            )

            segments = [
                {
                    'start': 0.0,
                    'end': 2.0,
                    'text': f'This is transcript {i} with unique word_{i}.'
                }
            ]

            transcript_mgr.save_transcript(
                job_id=job_id,
                text=segments[0]['text'],
                segments=segments,
                language='en'
            )

        # Search for common word
        results = db.search_transcriptions('transcript')
        assert len(results) == 3

        # Search for unique word
        results = db.search_transcriptions('unique')
        assert len(results) == 3

        # Search for specific transcript
        results = db.search_transcriptions('word_1')
        assert len(results) == 1
        assert 'word_1' in results[0]['text']

    def test_10_transaction_rollback(self, test_environment, sample_audio_file):
        """
        Test transaction rollback on error.
        """
        db = test_environment['db']

        initial_count_cursor = db.connection.execute(
            "SELECT COUNT(*) as count FROM transcription_jobs"
        )
        initial_count = initial_count_cursor.fetchone()['count']

        # Try to create job with invalid data (should fail)
        try:
            with db.transaction():
                db.connection.execute(
                    """
                    INSERT INTO transcription_jobs (
                        job_id, file_id, file_name, model_size, status
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ('test-uuid', 999999, 'test.wav', 'invalid_model', 'pending')
                )
                # This should fail due to foreign key constraint (file_id doesn't exist)

        except Exception:
            pass  # Expected to fail

        # Verify no job was created (rollback worked)
        final_count_cursor = db.connection.execute(
            "SELECT COUNT(*) as count FROM transcription_jobs"
        )
        final_count = final_count_cursor.fetchone()['count']

        assert final_count == initial_count, "Transaction should have rolled back"

    def test_11_cascade_delete(self, test_environment, sample_audio_file, sample_segments):
        """
        Test cascade delete functionality.
        """
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        # Create complete workflow
        file_mgr = test_environment['file_mgr']
        file_id, _ = file_mgr.upload_file(str(sample_audio_file))

        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        full_text = ' '.join([seg['text'] for seg in sample_segments])
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=full_text,
            segments=sample_segments,
            language='en'
        )

        # Verify all records exist
        assert db.get_job(job_id) is not None
        assert transcript_mgr.get_transcript(transcript_id) is not None

        # Delete job (should cascade to transcriptions)
        success = db.delete_job(job_id)
        assert success is True

        # Verify cascade delete
        assert db.get_job(job_id) is None

        # Transcription should be deleted
        with pytest.raises(Exception):
            transcript_mgr.get_transcript(transcript_id)

        # Versions should be deleted too
        cursor = db.connection.execute(
            "SELECT COUNT(*) as count FROM transcript_versions WHERE transcription_id = ?",
            (transcript_id,)
        )
        version_count = cursor.fetchone()['count']
        assert version_count == 0

    def test_12_concurrent_operations(
        self,
        test_environment,
        sample_audio_file,
        sample_segments
    ):
        """
        Test thread-safe concurrent operations.
        """
        import threading

        db = test_environment['db']
        results = {'success': 0, 'failed': 0}
        lock = threading.Lock()

        def create_job_and_transcript(thread_id):
            try:
                job_id = db.create_job(
                    file_path=str(sample_audio_file),
                    model_size='base',
                    task_type='transcribe'
                )

                transcript_mgr = test_environment['transcript_mgr']
                full_text = f'Thread {thread_id} transcript'
                segments = [
                    {'start': 0.0, 'end': 1.0, 'text': full_text}
                ]

                transcript_mgr.save_transcript(
                    job_id=job_id,
                    text=full_text,
                    segments=segments,
                    language='en'
                )

                with lock:
                    results['success'] += 1

            except Exception as e:
                print(f"Thread {thread_id} failed: {e}")
                with lock:
                    results['failed'] += 1

        # Create 5 concurrent threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_job_and_transcript, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all succeeded
        assert results['success'] == 5
        assert results['failed'] == 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_file_format(self, test_environment):
        """Test rejection of invalid file format."""
        from src.data.file_manager import FileFormatError

        file_mgr = test_environment['file_mgr']
        test_dir = test_environment['test_dir']

        # Create invalid file
        invalid_file = test_dir / 'test.exe'
        invalid_file.write_text('Invalid format')

        with pytest.raises(FileFormatError):
            file_mgr.upload_file(str(invalid_file))

    def test_file_size_validation(self, test_environment):
        """Test file size validation."""
        from src.data.file_manager import FileSizeError
        from src.data import storage_config

        file_mgr = test_environment['file_mgr']
        test_dir = test_environment['test_dir']

        # Create too small file
        small_file = test_dir / 'small.wav'
        small_file.write_bytes(b'x' * 100)  # Less than MIN_FILE_SIZE

        with pytest.raises(FileSizeError):
            file_mgr.upload_file(str(small_file))

    def test_nonexistent_file(self, test_environment):
        """Test handling of nonexistent file."""
        from src.data.file_manager import FileNotFoundError as FMFileNotFoundError

        file_mgr = test_environment['file_mgr']
        test_dir = test_environment['test_dir']

        nonexistent = test_dir / 'does_not_exist.wav'

        with pytest.raises(FMFileNotFoundError):
            file_mgr.upload_file(str(nonexistent))

    def test_invalid_segments(self, test_environment, sample_audio_file):
        """Test rejection of invalid segments."""
        from src.data.transcript_manager import TranscriptError

        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        # Invalid segments (missing required keys)
        invalid_segments = [
            {'start': 0.0, 'text': 'Missing end'}  # Missing 'end'
        ]

        with pytest.raises(TranscriptError):
            transcript_mgr.save_transcript(
                job_id=job_id,
                text='Test',
                segments=invalid_segments,
                language='en'
            )

    def test_version_not_found(self, test_environment, sample_audio_file, sample_segments):
        """Test handling of nonexistent version."""
        from src.data.transcript_manager import VersionNotFoundError

        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        job_id = db.create_job(
            file_path=str(sample_audio_file),
            model_size='base',
            task_type='transcribe'
        )

        full_text = ' '.join([seg['text'] for seg in sample_segments])
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=full_text,
            segments=sample_segments,
            language='en'
        )

        # Try to get nonexistent version
        with pytest.raises(VersionNotFoundError):
            transcript_mgr.get_transcript(transcript_id, version=999)


class TestPerformance:
    """Test performance characteristics."""

    def test_large_batch_operations(self, test_environment, sample_audio_file, sample_segments):
        """Test performance with large number of operations."""
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        start_time = time.time()

        # Create 100 jobs and transcripts
        for i in range(100):
            job_id = db.create_job(
                file_path=str(sample_audio_file),
                model_size='base',
                task_type='transcribe'
            )

            full_text = f'Batch test {i}'
            segments = [
                {'start': 0.0, 'end': 1.0, 'text': full_text}
            ]

            transcript_mgr.save_transcript(
                job_id=job_id,
                text=full_text,
                segments=segments,
                language='en'
            )

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 10 seconds)
        assert elapsed < 10.0, f"Batch operations too slow: {elapsed:.2f}s"

        # Verify all created
        stats = db.get_statistics()
        assert stats['total_jobs'] >= 100
        assert stats['total_transcripts'] >= 100

    def test_search_performance(self, test_environment, sample_audio_file):
        """Test full-text search performance."""
        db = test_environment['db']
        transcript_mgr = test_environment['transcript_mgr']

        # Create 50 transcripts with searchable content
        for i in range(50):
            job_id = db.create_job(
                file_path=str(sample_audio_file),
                model_size='base',
                task_type='transcribe'
            )

            segments = [
                {
                    'start': 0.0,
                    'end': 1.0,
                    'text': f'Performance test transcript number {i} with searchable content'
                }
            ]

            transcript_mgr.save_transcript(
                job_id=job_id,
                text=segments[0]['text'],
                segments=segments,
                language='en'
            )

        # Benchmark search
        start_time = time.time()
        results = db.search_transcriptions('searchable')
        elapsed = time.time() - start_time

        # Search should be fast (< 1 second)
        assert elapsed < 1.0, f"Search too slow: {elapsed:.2f}s"
        assert len(results) >= 50


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
