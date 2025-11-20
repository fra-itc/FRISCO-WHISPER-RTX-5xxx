#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Integration Tests for TranscriptionService
Tests the complete integration between transcription engine and data layer
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.transcription_service import TranscriptionService, TranscriptionServiceError
from src.core.transcription import TranscriptionResult
from src.data.database import DatabaseManager


class TestTranscriptionServiceIntegration(unittest.TestCase):
    """Integration tests for TranscriptionService."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for all tests."""
        # Create temporary directory for test files
        cls.test_dir = Path(tempfile.mkdtemp())
        cls.db_path = cls.test_dir / 'test_transcription.db'
        cls.audio_dir = cls.test_dir / 'audio'
        cls.output_dir = cls.test_dir / 'output'

        cls.audio_dir.mkdir(parents=True, exist_ok=True)
        cls.output_dir.mkdir(parents=True, exist_ok=True)

        # Create test audio file (mock WAV file)
        cls.test_audio_file = cls.audio_dir / 'test_audio.wav'
        cls._create_mock_wav_file(cls.test_audio_file)

        # Create test SRT file
        cls.test_srt_file = cls.output_dir / 'test_audio.srt'
        cls._create_mock_srt_file(cls.test_srt_file)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

    @staticmethod
    def _create_mock_wav_file(file_path: Path):
        """Create a mock WAV file for testing."""
        # Create a minimal valid WAV file (44 bytes header + 100 bytes data)
        with open(file_path, 'wb') as f:
            # RIFF header
            f.write(b'RIFF')
            f.write((136).to_bytes(4, 'little'))  # File size - 8
            f.write(b'WAVE')

            # fmt subchunk
            f.write(b'fmt ')
            f.write((16).to_bytes(4, 'little'))  # Subchunk size
            f.write((1).to_bytes(2, 'little'))   # Audio format (PCM)
            f.write((1).to_bytes(2, 'little'))   # Num channels
            f.write((16000).to_bytes(4, 'little'))  # Sample rate
            f.write((32000).to_bytes(4, 'little'))  # Byte rate
            f.write((2).to_bytes(2, 'little'))   # Block align
            f.write((16).to_bytes(2, 'little'))  # Bits per sample

            # data subchunk
            f.write(b'data')
            f.write((100).to_bytes(4, 'little'))  # Data size
            f.write(b'\x00' * 100)  # Audio data

    @staticmethod
    def _create_mock_srt_file(file_path: Path):
        """Create a mock SRT file for testing."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000
This is the first test segment.

2
00:00:05,000 --> 00:00:10,000
This is the second test segment.

3
00:00:10,000 --> 00:00:15,000
This is the third test segment.
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)

    def setUp(self):
        """Set up each test."""
        # Create fresh database for each test
        if self.db_path.exists():
            self.db_path.unlink()

    def tearDown(self):
        """Clean up after each test."""
        pass

    def test_service_initialization(self):
        """Test service initialization."""
        service = TranscriptionService(
            db_path=str(self.db_path),
            model_size='tiny'
        )

        self.assertIsNotNone(service.db)
        self.assertIsNotNone(service.file_manager)
        self.assertIsNotNone(service.transcript_manager)
        self.assertEqual(service.default_model_size, 'tiny')

        service.close()

    def test_context_manager(self):
        """Test service as context manager."""
        with TranscriptionService(db_path=str(self.db_path)) as service:
            self.assertIsNotNone(service.db)

        # Service should be closed after context exit
        # (connection should be None or closed)

    @patch('src.core.transcription.TranscriptionEngine.load_model')
    @patch('src.core.transcription.TranscriptionEngine.transcribe')
    @patch('src.core.audio_processor.AudioProcessor.get_duration')
    @patch('src.core.audio_processor.AudioProcessor.get_metadata')
    @patch('src.core.audio_processor.AudioProcessor.is_wav_compatible')
    def test_transcribe_file_complete_workflow(
        self,
        mock_is_wav,
        mock_metadata,
        mock_duration,
        mock_transcribe,
        mock_load_model
    ):
        """Test complete transcription workflow."""
        # Setup mocks
        mock_load_model.return_value = True
        mock_is_wav.return_value = True
        mock_duration.return_value = 15.0

        mock_metadata_obj = Mock()
        mock_metadata_obj.format = 'wav'
        mock_metadata_obj.sample_rate = 16000
        mock_metadata.return_value = mock_metadata_obj

        # Mock transcription result
        mock_result = TranscriptionResult(
            success=True,
            output_path=self.test_srt_file,
            segments_count=3,
            language='en',
            language_probability=0.95,
            duration=2.5
        )
        mock_transcribe.return_value = mock_result

        # Create service and transcribe
        with TranscriptionService(db_path=str(self.db_path), model_size='tiny') as service:
            result = service.transcribe_file(
                file_path=str(self.test_audio_file),
                language='en'
            )

            # Verify result
            self.assertTrue(result['success'])
            self.assertIn('job_id', result)
            self.assertIn('file_id', result)
            self.assertIn('transcript_id', result)
            self.assertEqual(result['language'], 'en')
            self.assertEqual(result['segments_count'], 3)

            # Verify job in database
            job = service.db.get_job(result['job_id'])
            self.assertIsNotNone(job)
            self.assertEqual(job['status'], 'completed')
            self.assertEqual(job['detected_language'], 'en')

            # Verify transcript in database
            transcript = service.get_transcript(result['transcript_id'])
            self.assertIsNotNone(transcript)
            self.assertEqual(len(transcript['segments']), 3)

    @patch('src.core.transcription.TranscriptionEngine.load_model')
    @patch('src.core.transcription.TranscriptionEngine.transcribe')
    @patch('src.core.audio_processor.AudioProcessor.get_duration')
    @patch('src.core.audio_processor.AudioProcessor.get_metadata')
    @patch('src.core.audio_processor.AudioProcessor.is_wav_compatible')
    def test_transcribe_file_with_progress_callback(
        self,
        mock_is_wav,
        mock_metadata,
        mock_duration,
        mock_transcribe,
        mock_load_model
    ):
        """Test transcription with progress callback."""
        # Setup mocks
        mock_load_model.return_value = True
        mock_is_wav.return_value = True
        mock_duration.return_value = 15.0

        mock_metadata_obj = Mock()
        mock_metadata_obj.format = 'wav'
        mock_metadata_obj.sample_rate = 16000
        mock_metadata.return_value = mock_metadata_obj

        # Mock transcription with progress callback
        def transcribe_side_effect(*args, **kwargs):
            callback = kwargs.get('progress_callback')
            if callback:
                # Simulate progress updates
                callback({
                    'segment_number': 1,
                    'text': 'Test segment',
                    'start': 0.0,
                    'end': 5.0,
                    'progress_pct': 33.3,
                    'audio_duration': 15.0
                })

            return TranscriptionResult(
                success=True,
                output_path=self.test_srt_file,
                segments_count=3,
                language='en',
                language_probability=0.95,
                duration=2.5
            )

        mock_transcribe.side_effect = transcribe_side_effect

        # Track progress callbacks
        progress_calls = []

        def progress_handler(data):
            progress_calls.append(data)

        # Transcribe with callback
        with TranscriptionService(db_path=str(self.db_path), model_size='tiny') as service:
            result = service.transcribe_file(
                file_path=str(self.test_audio_file),
                progress_callback=progress_handler
            )

            self.assertTrue(result['success'])
            self.assertGreater(len(progress_calls), 0)

    @patch('src.core.transcription.TranscriptionEngine.load_model')
    @patch('src.core.transcription.TranscriptionEngine.transcribe')
    @patch('src.core.audio_processor.AudioProcessor.get_duration')
    @patch('src.core.audio_processor.AudioProcessor.get_metadata')
    @patch('src.core.audio_processor.AudioProcessor.is_wav_compatible')
    def test_transcribe_file_failure_rollback(
        self,
        mock_is_wav,
        mock_metadata,
        mock_duration,
        mock_transcribe,
        mock_load_model
    ):
        """Test that failed transcription updates job status correctly."""
        # Setup mocks
        mock_load_model.return_value = True
        mock_is_wav.return_value = True
        mock_duration.return_value = 15.0

        mock_metadata_obj = Mock()
        mock_metadata_obj.format = 'wav'
        mock_metadata_obj.sample_rate = 16000
        mock_metadata.return_value = mock_metadata_obj

        # Mock transcription failure
        mock_result = TranscriptionResult(
            success=False,
            error="Transcription engine error"
        )
        mock_transcribe.return_value = mock_result

        # Transcribe (should fail)
        with TranscriptionService(db_path=str(self.db_path), model_size='tiny') as service:
            with self.assertRaises(TranscriptionServiceError):
                service.transcribe_file(file_path=str(self.test_audio_file))

            # Verify job marked as failed in database
            recent_jobs = service.db.get_recent_jobs(limit=1)
            self.assertEqual(len(recent_jobs), 1)
            self.assertEqual(recent_jobs[0]['status'], 'failed')
            self.assertIsNotNone(recent_jobs[0]['error_message'])

    def test_transcribe_file_not_found(self):
        """Test transcription with non-existent file."""
        with TranscriptionService(db_path=str(self.db_path)) as service:
            with self.assertRaises(TranscriptionServiceError) as ctx:
                service.transcribe_file(
                    file_path=str(self.test_dir / 'nonexistent.wav')
                )

            self.assertIn('File not found', str(ctx.exception))

    @patch('src.core.transcription.TranscriptionEngine.load_model')
    @patch('src.core.transcription.TranscriptionEngine.transcribe')
    @patch('src.core.audio_processor.AudioProcessor.get_duration')
    @patch('src.core.audio_processor.AudioProcessor.get_metadata')
    @patch('src.core.audio_processor.AudioProcessor.is_wav_compatible')
    def test_batch_transcription(
        self,
        mock_is_wav,
        mock_metadata,
        mock_duration,
        mock_transcribe,
        mock_load_model
    ):
        """Test batch transcription."""
        # Create multiple test files
        test_files = []
        for i in range(3):
            test_file = self.audio_dir / f'test_audio_{i}.wav'
            self._create_mock_wav_file(test_file)
            test_files.append(str(test_file))

        # Setup mocks
        mock_load_model.return_value = True
        mock_is_wav.return_value = True
        mock_duration.return_value = 15.0

        mock_metadata_obj = Mock()
        mock_metadata_obj.format = 'wav'
        mock_metadata_obj.sample_rate = 16000
        mock_metadata.return_value = mock_metadata_obj

        mock_result = TranscriptionResult(
            success=True,
            output_path=self.test_srt_file,
            segments_count=3,
            language='en',
            language_probability=0.95,
            duration=2.5
        )
        mock_transcribe.return_value = mock_result

        # Track batch progress
        batch_progress_calls = []

        def batch_progress_handler(file_idx, total, result):
            batch_progress_calls.append((file_idx, total, result['success']))

        # Batch transcribe
        with TranscriptionService(db_path=str(self.db_path), model_size='tiny') as service:
            results = service.transcribe_batch(
                file_paths=test_files,
                batch_progress_callback=batch_progress_handler,
                language='en'
            )

            # Verify results
            self.assertEqual(len(results), 3)
            self.assertTrue(all(r['success'] for r in results))
            self.assertEqual(len(batch_progress_calls), 3)

    @patch('src.core.transcription.TranscriptionEngine.load_model')
    @patch('src.core.transcription.TranscriptionEngine.transcribe')
    @patch('src.core.audio_processor.AudioProcessor.get_duration')
    @patch('src.core.audio_processor.AudioProcessor.get_metadata')
    @patch('src.core.audio_processor.AudioProcessor.is_wav_compatible')
    def test_file_deduplication(
        self,
        mock_is_wav,
        mock_metadata,
        mock_duration,
        mock_transcribe,
        mock_load_model
    ):
        """Test that duplicate files are detected."""
        # Setup mocks
        mock_load_model.return_value = True
        mock_is_wav.return_value = True
        mock_duration.return_value = 15.0

        mock_metadata_obj = Mock()
        mock_metadata_obj.format = 'wav'
        mock_metadata_obj.sample_rate = 16000
        mock_metadata.return_value = mock_metadata_obj

        mock_result = TranscriptionResult(
            success=True,
            output_path=self.test_srt_file,
            segments_count=3,
            language='en',
            language_probability=0.95,
            duration=2.5
        )
        mock_transcribe.return_value = mock_result

        # Transcribe same file twice
        with TranscriptionService(db_path=str(self.db_path), model_size='tiny') as service:
            result1 = service.transcribe_file(file_path=str(self.test_audio_file))
            result2 = service.transcribe_file(file_path=str(self.test_audio_file))

            # Should use same file_id
            self.assertEqual(result1['file_id'], result2['file_id'])
            self.assertFalse(result1['was_duplicate'])
            self.assertTrue(result2['was_duplicate'])

    @patch('src.core.transcription.TranscriptionEngine.load_model')
    @patch('src.core.transcription.TranscriptionEngine.transcribe')
    @patch('src.core.audio_processor.AudioProcessor.get_duration')
    @patch('src.core.audio_processor.AudioProcessor.get_metadata')
    @patch('src.core.audio_processor.AudioProcessor.is_wav_compatible')
    def test_export_transcript(
        self,
        mock_is_wav,
        mock_metadata,
        mock_duration,
        mock_transcribe,
        mock_load_model
    ):
        """Test transcript export to different formats."""
        # Setup mocks
        mock_load_model.return_value = True
        mock_is_wav.return_value = True
        mock_duration.return_value = 15.0

        mock_metadata_obj = Mock()
        mock_metadata_obj.format = 'wav'
        mock_metadata_obj.sample_rate = 16000
        mock_metadata.return_value = mock_metadata_obj

        mock_result = TranscriptionResult(
            success=True,
            output_path=self.test_srt_file,
            segments_count=3,
            language='en',
            language_probability=0.95,
            duration=2.5
        )
        mock_transcribe.return_value = mock_result

        # Transcribe
        with TranscriptionService(db_path=str(self.db_path), model_size='tiny') as service:
            result = service.transcribe_file(file_path=str(self.test_audio_file))
            transcript_id = result['transcript_id']

            # Test exports
            formats = ['srt', 'vtt', 'txt', 'json']

            for fmt in formats:
                output_path = self.output_dir / f'export.{fmt}'
                content = service.export_transcript(
                    transcript_id=transcript_id,
                    format_name=fmt,
                    output_path=str(output_path)
                )

                self.assertTrue(output_path.exists())
                self.assertGreater(len(content), 0)

    @patch('src.core.transcription.TranscriptionEngine.load_model')
    @patch('src.core.transcription.TranscriptionEngine.transcribe')
    @patch('src.core.audio_processor.AudioProcessor.get_duration')
    @patch('src.core.audio_processor.AudioProcessor.get_metadata')
    @patch('src.core.audio_processor.AudioProcessor.is_wav_compatible')
    def test_get_statistics(
        self,
        mock_is_wav,
        mock_metadata,
        mock_duration,
        mock_transcribe,
        mock_load_model
    ):
        """Test getting system statistics."""
        # Setup mocks
        mock_load_model.return_value = True
        mock_is_wav.return_value = True
        mock_duration.return_value = 15.0

        mock_metadata_obj = Mock()
        mock_metadata_obj.format = 'wav'
        mock_metadata_obj.sample_rate = 16000
        mock_metadata.return_value = mock_metadata_obj

        mock_result = TranscriptionResult(
            success=True,
            output_path=self.test_srt_file,
            segments_count=3,
            language='en',
            language_probability=0.95,
            duration=2.5
        )
        mock_transcribe.return_value = mock_result

        # Transcribe some files
        with TranscriptionService(db_path=str(self.db_path), model_size='tiny') as service:
            service.transcribe_file(file_path=str(self.test_audio_file))

            # Get statistics
            stats = service.get_statistics()

            self.assertIn('database', stats)
            self.assertIn('storage', stats)
            self.assertIn('transcripts', stats)

            self.assertGreater(stats['database'].get('total_jobs', 0), 0)
            self.assertGreater(stats['storage'].get('total_files', 0), 0)
            self.assertGreater(stats['transcripts'].get('total_transcripts', 0), 0)

    def test_parse_srt_timestamp(self):
        """Test SRT timestamp parsing."""
        service = TranscriptionService(db_path=str(self.db_path))

        # Test various timestamps
        tests = [
            ('00:00:00,000', 0.0),
            ('00:00:05,000', 5.0),
            ('00:01:00,000', 60.0),
            ('01:00:00,000', 3600.0),
            ('00:00:00,500', 0.5),
            ('00:00:10,250', 10.25)
        ]

        for timestamp_str, expected_seconds in tests:
            result = service._parse_srt_timestamp(timestamp_str)
            self.assertAlmostEqual(result, expected_seconds, places=2)

        service.close()

    def test_parse_srt_file(self):
        """Test SRT file parsing."""
        service = TranscriptionService(db_path=str(self.db_path))

        segments = service._parse_srt_file(self.test_srt_file)

        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0]['start'], 0.0)
        self.assertEqual(segments[0]['end'], 5.0)
        self.assertEqual(segments[0]['text'], 'This is the first test segment.')

        service.close()


class TestTranscriptionServiceErrorHandling(unittest.TestCase):
    """Test error handling in TranscriptionService."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / 'test_transcription.db'

    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_invalid_file_path(self):
        """Test handling of invalid file path."""
        with TranscriptionService(db_path=str(self.db_path)) as service:
            with self.assertRaises(TranscriptionServiceError):
                service.transcribe_file(file_path='/nonexistent/path/file.wav')

    def test_database_error_handling(self):
        """Test handling of database errors."""
        # Create service with read-only database (to simulate error)
        # This test is tricky - would need to mock database errors


if __name__ == '__main__':
    unittest.main(verbosity=2)
