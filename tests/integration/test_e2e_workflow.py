#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - End-to-End Workflow Test
Comprehensive test of complete system workflow
"""

import pytest
import tempfile
import shutil
import wave
import struct
from pathlib import Path
from datetime import datetime

from src.data.database import DatabaseManager
from src.data.file_manager import FileManager
from src.data.transcript_manager import TranscriptManager
from src.data.format_converters import FormatConverter


@pytest.fixture(scope='module')
def e2e_environment():
    """
    Create comprehensive E2E test environment.
    """
    test_dir = Path(tempfile.mkdtemp(prefix='frisco_e2e_'))

    # Setup paths
    db_path = test_dir / 'e2e.db'
    upload_dir = test_dir / 'uploads'
    transcripts_dir = test_dir / 'transcripts'
    exports_dir = test_dir / 'exports'

    for d in [upload_dir, transcripts_dir, exports_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Initialize components
    db_manager = DatabaseManager(str(db_path))
    file_manager = FileManager(db_manager, base_dir=upload_dir)
    transcript_manager = TranscriptManager(db_manager)

    env = {
        'test_dir': test_dir,
        'db_path': db_path,
        'upload_dir': upload_dir,
        'transcripts_dir': transcripts_dir,
        'exports_dir': exports_dir,
        'db': db_manager,
        'file_mgr': file_manager,
        'transcript_mgr': transcript_manager
    }

    yield env

    # Cleanup
    db_manager.close()
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def sample_audio(e2e_environment):
    """Create sample audio file for testing."""
    test_dir = e2e_environment['test_dir']
    audio_file = test_dir / 'sample_audio.wav'

    # Create 2-second WAV file
    sample_rate = 16000
    duration = 2
    num_samples = sample_rate * duration

    with wave.open(str(audio_file), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(num_samples):
            value = int(32767 * 0.1 * (i % 100) / 100)
            wav_file.writeframes(struct.pack('<h', value))

    return audio_file


@pytest.fixture
def sample_transcript_data():
    """Sample transcript with segments."""
    return {
        'text': 'This is a test transcription. It has multiple sentences. And some punctuation!',
        'language': 'en',
        'segments': [
            {
                'start': 0.0,
                'end': 2.5,
                'text': 'This is a test transcription.'
            },
            {
                'start': 2.5,
                'end': 4.5,
                'text': 'It has multiple sentences.'
            },
            {
                'start': 4.5,
                'end': 6.5,
                'text': 'And some punctuation!'
            }
        ]
    }


class TestCompleteE2EWorkflow:
    """Test complete end-to-end workflow."""

    def test_complete_workflow(self, e2e_environment, sample_audio, sample_transcript_data):
        """
        Test complete workflow: upload → transcribe → version → export
        """
        db = e2e_environment['db']
        file_mgr = e2e_environment['file_mgr']
        transcript_mgr = e2e_environment['transcript_mgr']
        exports_dir = e2e_environment['exports_dir']

        # STEP 1: Upload audio file
        file_id, is_new = file_mgr.upload_file(str(sample_audio))
        assert is_new is True
        assert file_id > 0

        # Verify file info
        file_info = file_mgr.get_file(file_id)
        assert file_info is not None
        assert file_info['original_name'] == 'sample_audio.wav'
        assert file_info['format'] == 'wav'

        # STEP 2: Create transcription job
        job_id = db.create_job(
            file_path=str(sample_audio),
            model_size='base',
            task_type='transcribe',
            language='en',
            compute_type='float32',
            device='cpu',
            duration_seconds=2.0
        )

        assert job_id is not None
        job = db.get_job(job_id)
        assert job['status'] == 'pending'
        assert job['file_id'] == file_id

        # STEP 3: Update job to processing
        db.update_job(
            job_id,
            status='processing',
            started_at=datetime.now()
        )

        job = db.get_job(job_id)
        assert job['status'] == 'processing'

        # STEP 4: Save transcription
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=sample_transcript_data['text'],
            segments=sample_transcript_data['segments'],
            language=sample_transcript_data['language']
        )

        assert transcript_id > 0

        # Verify transcript
        transcript = transcript_mgr.get_transcript(transcript_id)
        assert transcript is not None
        assert transcript['job_id'] == job_id
        assert transcript['language'] == 'en'
        assert transcript['segment_count'] == 3
        assert transcript['version_number'] == 1

        # STEP 5: Update job to completed
        db.update_job(
            job_id,
            status='completed',
            completed_at=datetime.now(),
            processing_time_seconds=5.5,
            detected_language='en',
            language_probability=0.99
        )

        job = db.get_job(job_id)
        assert job['status'] == 'completed'
        assert job['processing_time_seconds'] == 5.5
        assert job['detected_language'] == 'en'

        # STEP 6: Create transcript version (edit)
        updated_segments = sample_transcript_data['segments'].copy()
        updated_segments[0]['text'] = 'This is an EDITED test transcription.'
        updated_text = ' '.join([seg['text'] for seg in updated_segments])

        version_num = transcript_mgr.update_transcript(
            transcript_id=transcript_id,
            text=updated_text,
            segments=updated_segments,
            created_by='e2e_test',
            change_note='Fixed first sentence'
        )

        assert version_num == 2

        # Verify versions
        versions = transcript_mgr.get_versions(transcript_id)
        assert len(versions) == 2
        assert versions[0]['version_number'] == 2
        assert versions[0]['is_current'] == 1
        assert versions[1]['version_number'] == 1
        assert versions[1]['is_current'] == 0

        # STEP 7: Export to multiple formats
        export_formats = ['srt', 'vtt', 'json', 'txt', 'csv']

        for format_name in export_formats:
            output_path = exports_dir / f'test.{format_name}'

            content = transcript_mgr.export_transcript(
                transcript_id=transcript_id,
                format_name=format_name,
                output_path=str(output_path)
            )

            assert content is not None
            assert len(content) > 0
            assert output_path.exists()

            # Format-specific validation
            if format_name == 'srt':
                assert '00:00:00,000 --> 00:00:02,500' in content
                assert 'EDITED' in content

            elif format_name == 'vtt':
                assert 'WEBVTT' in content

            elif format_name == 'json':
                import json
                data = json.loads(content)
                assert 'segments' in data
                assert len(data['segments']) == 3

            elif format_name == 'txt':
                assert 'EDITED' in content

            elif format_name == 'csv':
                assert 'index,start,end' in content

        # STEP 8: Verify export history
        history = transcript_mgr.get_version_history(transcript_id)
        assert history['export_count'] == len(export_formats)

        # STEP 9: Test search functionality
        results = db.search_transcriptions('EDITED')
        assert len(results) >= 1
        found = False
        for result in results:
            if result['id'] == transcript_id:
                found = True
                break
        assert found

        # STEP 10: Test version comparison
        comparison = transcript_mgr.compare_versions(
            transcript_id=transcript_id,
            version1=1,
            version2=2
        )

        assert comparison is not None
        assert comparison['version1']['number'] == 1
        assert comparison['version2']['number'] == 2
        text_diff = comparison['text_diff']
        assert text_diff['old_word_count'] > 0
        assert text_diff['new_word_count'] > 0

        # STEP 11: Test rollback
        version_num = transcript_mgr.rollback_to_version(
            transcript_id=transcript_id,
            version_number=1,
            created_by='e2e_test',
            change_note='Rollback test'
        )

        assert version_num == 3

        # Verify rollback
        current = transcript_mgr.get_transcript(transcript_id)
        assert current['version_number'] == 3
        assert 'EDITED' not in current['text']

        # STEP 12: Verify database statistics
        stats = db.get_statistics()
        assert stats['total_jobs'] >= 1
        assert stats['completed_jobs'] >= 1
        assert stats['total_files'] >= 1
        assert stats['total_transcripts'] >= 1

    def test_data_integrity_throughout_workflow(self, e2e_environment, sample_audio, sample_transcript_data):
        """
        Test data integrity is maintained throughout workflow.
        """
        db = e2e_environment['db']
        file_mgr = e2e_environment['file_mgr']
        transcript_mgr = e2e_environment['transcript_mgr']

        # Upload and create job
        file_id, _ = file_mgr.upload_file(str(sample_audio))
        job_id = db.create_job(
            file_path=str(sample_audio),
            model_size='small',
            task_type='transcribe'
        )

        # Save transcript
        transcript_id = transcript_mgr.save_transcript(
            job_id=job_id,
            text=sample_transcript_data['text'],
            segments=sample_transcript_data['segments'],
            language='en'
        )

        # Retrieve and verify
        transcript = transcript_mgr.get_transcript(transcript_id)
        assert transcript['text'] == sample_transcript_data['text']
        assert len(transcript['segments']) == len(sample_transcript_data['segments'])

        # Verify all segments match
        for i, segment in enumerate(transcript['segments']):
            original = sample_transcript_data['segments'][i]
            assert segment['start'] == original['start']
            assert segment['end'] == original['end']
            assert segment['text'] == original['text']

    def test_concurrent_workflow_execution(self, e2e_environment, sample_audio, sample_transcript_data):
        """
        Test multiple concurrent workflows don't interfere.
        """
        import threading

        db = e2e_environment['db']
        file_mgr = e2e_environment['file_mgr']
        transcript_mgr = e2e_environment['transcript_mgr']

        results = {'success': 0, 'failed': 0}
        lock = threading.Lock()

        def run_workflow(thread_id):
            try:
                # Upload
                file_id, _ = file_mgr.upload_file(str(sample_audio))

                # Create job
                job_id = db.create_job(
                    file_path=str(sample_audio),
                    model_size='base',
                    task_type='transcribe'
                )

                # Save transcript
                text = f'Thread {thread_id} transcript'
                segments = [{'start': 0.0, 'end': 1.0, 'text': text}]

                transcript_id = transcript_mgr.save_transcript(
                    job_id=job_id,
                    text=text,
                    segments=segments,
                    language='en'
                )

                # Verify
                transcript = transcript_mgr.get_transcript(transcript_id)
                assert transcript['text'] == text

                with lock:
                    results['success'] += 1

            except Exception as e:
                print(f"Thread {thread_id} failed: {e}")
                with lock:
                    results['failed'] += 1

        # Run 3 concurrent workflows
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_workflow, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert results['success'] == 3
        assert results['failed'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
