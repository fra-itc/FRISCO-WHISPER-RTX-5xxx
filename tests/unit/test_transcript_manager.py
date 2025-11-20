"""
Unit tests for transcript manager and versioning system.

Tests transcript storage, version management, format conversion,
and all related operations.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data import (
    DatabaseManager,
    TranscriptManager,
    FormatConverter,
    DiffGenerator,
    TranscriptError,
    TranscriptNotFoundError,
    VersionNotFoundError
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    db_path = tmp_path / "test_transcripts.db"
    yield str(db_path)


@pytest.fixture
def db_manager(temp_db_path):
    """Create a DatabaseManager instance."""
    return DatabaseManager(temp_db_path)


@pytest.fixture
def transcript_manager(db_manager):
    """Create a TranscriptManager instance."""
    return TranscriptManager(db_manager)


@pytest.fixture
def sample_segments():
    """Sample transcript segments for testing."""
    return [
        {"start": 0.0, "end": 5.0, "text": "This is the first segment."},
        {"start": 5.0, "end": 10.0, "text": "This is the second segment."},
        {"start": 10.0, "end": 15.0, "text": "This is the third segment."}
    ]


@pytest.fixture
def sample_text():
    """Sample full text for testing."""
    return "This is the first segment. This is the second segment. This is the third segment."


@pytest.fixture
def sample_transcript(transcript_manager, db_manager, sample_segments, sample_text):
    """Create a sample transcript for testing."""
    # Create a job first
    audio_file = Path(__file__).parent / "fixtures" / "sample.mp3"
    if not audio_file.exists():
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        audio_file.write_text("fake audio")

    job_id = db_manager.create_job(
        file_path=str(audio_file),
        model_size='medium',
        language='en'
    )

    # Save transcript
    transcript_id = transcript_manager.save_transcript(
        job_id=job_id,
        text=sample_text,
        segments=sample_segments,
        language='en'
    )

    return transcript_id


# ============================================================================
# Tests for FormatConverter
# ============================================================================

class TestFormatConverter:
    """Test suite for format conversion operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_srt_basic(self, sample_segments):
        """Test basic SRT conversion."""
        converter = FormatConverter()
        srt = converter.to_srt(sample_segments)

        assert "1" in srt
        assert "00:00:00,000 --> 00:00:05,000" in srt
        assert "This is the first segment." in srt
        assert "2" in srt
        assert "3" in srt

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_srt_empty(self):
        """Test SRT conversion with empty segments."""
        converter = FormatConverter()
        srt = converter.to_srt([])
        assert srt == ""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_vtt_basic(self, sample_segments):
        """Test basic VTT conversion."""
        converter = FormatConverter()
        vtt = converter.to_vtt(sample_segments)

        assert vtt.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:05.000" in vtt
        assert "This is the first segment." in vtt

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_vtt_with_metadata(self, sample_segments):
        """Test VTT conversion with metadata."""
        converter = FormatConverter()
        metadata = {'language': 'en', 'title': 'Test Video'}
        vtt = converter.to_vtt(sample_segments, metadata=metadata)

        assert "Language: en" in vtt
        assert "Title: Test Video" in vtt

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_json_basic(self, sample_segments, sample_text):
        """Test JSON conversion."""
        converter = FormatConverter()
        json_str = converter.to_json(sample_segments, text=sample_text)

        data = json.loads(json_str)
        assert data['format'] == 'whisper-json'
        assert data['segment_count'] == 3
        assert data['text'] == sample_text
        assert len(data['segments']) == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_json_with_metadata(self, sample_segments):
        """Test JSON conversion with metadata."""
        converter = FormatConverter()
        metadata = {'language': 'en', 'duration': 15.0}
        json_str = converter.to_json(sample_segments, metadata=metadata)

        data = json.loads(json_str)
        assert data['metadata']['language'] == 'en'
        assert data['metadata']['duration'] == 15.0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_txt_without_timestamps(self, sample_segments):
        """Test plain text conversion without timestamps."""
        converter = FormatConverter()
        txt = converter.to_txt(sample_segments, include_timestamps=False)

        assert "This is the first segment." in txt
        assert "[" not in txt
        assert "\n" in txt

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_txt_with_timestamps(self, sample_segments):
        """Test plain text conversion with timestamps."""
        converter = FormatConverter()
        txt = converter.to_txt(sample_segments, include_timestamps=True)

        assert "[00:00] This is the first segment." in txt
        assert "[00:05] This is the second segment." in txt

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_csv_basic(self, sample_segments):
        """Test CSV conversion."""
        converter = FormatConverter()
        csv = converter.to_csv(sample_segments)

        assert "index,start,end,duration,text" in csv
        assert "1,0.000,5.000,5.000" in csv
        assert "This is the first segment." in csv

    @pytest.mark.unit
    @pytest.mark.fast
    def test_convert_dispatch(self, sample_segments):
        """Test format conversion dispatcher."""
        converter = FormatConverter()

        # Test all formats
        srt = converter.convert(sample_segments, 'srt')
        assert "1" in srt

        vtt = converter.convert(sample_segments, 'vtt')
        assert "WEBVTT" in vtt

        json_str = converter.convert(sample_segments, 'json')
        assert "whisper-json" in json_str

        txt = converter.convert(sample_segments, 'txt')
        assert "first segment" in txt

        csv = converter.convert(sample_segments, 'csv')
        assert "index,start" in csv

    @pytest.mark.unit
    @pytest.mark.fast
    def test_convert_invalid_format(self, sample_segments):
        """Test conversion with invalid format."""
        converter = FormatConverter()

        with pytest.raises(ValueError, match="Unsupported format"):
            converter.convert(sample_segments, 'xyz')

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_segments_valid(self, sample_segments):
        """Test segment validation with valid data."""
        assert FormatConverter.validate_segments(sample_segments)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_segments_missing_key(self):
        """Test segment validation with missing keys."""
        invalid_segments = [
            {"start": 0.0, "end": 5.0}  # Missing 'text'
        ]
        assert not FormatConverter.validate_segments(invalid_segments)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_segments_invalid_time(self):
        """Test segment validation with invalid timestamps."""
        invalid_segments = [
            {"start": 5.0, "end": 0.0, "text": "Invalid"}  # end < start
        ]
        assert not FormatConverter.validate_segments(invalid_segments)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        formats = FormatConverter.get_supported_formats()
        assert 'srt' in formats
        assert 'vtt' in formats
        assert 'json' in formats
        assert 'txt' in formats
        assert 'csv' in formats

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_format_info(self):
        """Test getting format information."""
        info = FormatConverter.get_format_info('srt')
        assert info['name'] == 'SubRip'
        assert info['extension'] == '.srt'
        assert info['mime_type'] == 'application/x-subrip'

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_json(self, sample_segments, sample_text):
        """Test parsing JSON back to segments."""
        converter = FormatConverter()
        json_str = converter.to_json(sample_segments, text=sample_text)

        result = converter.from_json(json_str)
        assert result['text'] == sample_text
        assert len(result['segments']) == 3
        assert result['segments'][0]['text'] == "This is the first segment."


# ============================================================================
# Tests for DiffGenerator
# ============================================================================

class TestDiffGenerator:
    """Test suite for diff generation operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_text_diff_basic(self):
        """Test basic text diff."""
        diff_gen = DiffGenerator()

        old_text = "This is the original text."
        new_text = "This is the modified text with more content."

        diff = diff_gen.text_diff(old_text, new_text)

        assert diff['old_length'] == len(old_text)
        assert diff['new_length'] == len(new_text)
        assert diff['char_diff'] > 0
        assert diff['old_word_count'] == 5
        assert diff['new_word_count'] == 8

    @pytest.mark.unit
    @pytest.mark.fast
    def test_segment_diff_basic(self):
        """Test basic segment diff."""
        diff_gen = DiffGenerator()

        old_segments = [
            {"start": 0.0, "end": 5.0, "text": "First"},
            {"start": 5.0, "end": 10.0, "text": "Second"}
        ]

        new_segments = [
            {"start": 0.0, "end": 5.0, "text": "First"},
            {"start": 5.0, "end": 10.0, "text": "Second"},
            {"start": 10.0, "end": 15.0, "text": "Third"}
        ]

        diff = diff_gen.segment_diff(old_segments, new_segments)

        assert diff['old_segment_count'] == 2
        assert diff['new_segment_count'] == 3
        assert diff['segment_diff'] == 1
        assert diff['matching_segments'] == 2


# ============================================================================
# Tests for TranscriptManager
# ============================================================================

class TestTranscriptManager:
    """Test suite for transcript management operations."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_save_transcript(self, transcript_manager, db_manager, sample_segments, sample_text):
        """Test saving a new transcript."""
        audio_file = Path(__file__).parent / "fixtures" / "test.mp3"
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        audio_file.write_text("fake audio")

        job_id = db_manager.create_job(
            file_path=str(audio_file),
            model_size='medium',
            language='en'
        )

        transcript_id = transcript_manager.save_transcript(
            job_id=job_id,
            text=sample_text,
            segments=sample_segments,
            language='en'
        )

        assert transcript_id > 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_save_transcript_invalid_segments(self, transcript_manager, db_manager):
        """Test saving transcript with invalid segments."""
        audio_file = Path(__file__).parent / "fixtures" / "test2.mp3"
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        audio_file.write_text("fake audio")

        job_id = db_manager.create_job(
            file_path=str(audio_file),
            model_size='medium'
        )

        invalid_segments = [{"start": 0.0}]  # Missing required fields

        with pytest.raises(TranscriptError):
            transcript_manager.save_transcript(
                job_id=job_id,
                text="text",
                segments=invalid_segments
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_transcript_current(self, transcript_manager, sample_transcript):
        """Test getting current version of transcript."""
        transcript = transcript_manager.get_transcript(sample_transcript)

        assert transcript['id'] == sample_transcript
        assert transcript['version_number'] == 1
        assert len(transcript['segments']) == 3
        assert transcript['text']

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_transcript_not_found(self, transcript_manager):
        """Test getting non-existent transcript."""
        with pytest.raises(TranscriptNotFoundError):
            transcript_manager.get_transcript(99999)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_transcript(self, transcript_manager, sample_transcript):
        """Test updating transcript creates new version."""
        new_segments = [
            {"start": 0.0, "end": 7.0, "text": "Updated first segment."},
            {"start": 7.0, "end": 15.0, "text": "Updated second segment."}
        ]
        new_text = "Updated first segment. Updated second segment."

        version = transcript_manager.update_transcript(
            transcript_id=sample_transcript,
            text=new_text,
            segments=new_segments,
            created_by='test_user',
            change_note='Updated for testing'
        )

        assert version == 2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_versions(self, transcript_manager, sample_transcript):
        """Test getting all versions of a transcript."""
        # Update to create version 2
        new_segments = [
            {"start": 0.0, "end": 10.0, "text": "Updated segment."}
        ]
        transcript_manager.update_transcript(
            sample_transcript,
            "Updated segment.",
            new_segments
        )

        versions = transcript_manager.get_versions(sample_transcript)

        assert len(versions) >= 2
        assert versions[0]['version_number'] == 2  # Most recent first
        assert versions[1]['version_number'] == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_specific_version(self, transcript_manager, sample_transcript):
        """Test getting specific version of transcript."""
        # Create version 2
        new_segments = [{"start": 0.0, "end": 5.0, "text": "Version 2"}]
        transcript_manager.update_transcript(
            sample_transcript,
            "Version 2",
            new_segments
        )

        # Get version 1
        v1 = transcript_manager.get_transcript(sample_transcript, version=1)
        assert v1['version_number'] == 1
        assert "first segment" in v1['text']

        # Get version 2
        v2 = transcript_manager.get_transcript(sample_transcript, version=2)
        assert v2['version_number'] == 2
        assert "Version 2" in v2['text']

    @pytest.mark.unit
    @pytest.mark.fast
    def test_compare_versions(self, transcript_manager, sample_transcript):
        """Test comparing two versions."""
        # Create version 2
        new_segments = [
            {"start": 0.0, "end": 5.0, "text": "Changed segment."}
        ]
        transcript_manager.update_transcript(
            sample_transcript,
            "Changed segment.",
            new_segments
        )

        comparison = transcript_manager.compare_versions(
            sample_transcript,
            version1=1,
            version2=2
        )

        assert comparison['version1']['number'] == 1
        assert comparison['version2']['number'] == 2
        assert 'text_diff' in comparison
        assert 'segment_diff' in comparison

    @pytest.mark.unit
    @pytest.mark.fast
    def test_rollback_to_version(self, transcript_manager, sample_transcript):
        """Test rolling back to previous version."""
        # Create version 2
        new_segments = [{"start": 0.0, "end": 5.0, "text": "Version 2"}]
        transcript_manager.update_transcript(
            sample_transcript,
            "Version 2",
            new_segments
        )

        # Rollback to version 1
        new_version = transcript_manager.rollback_to_version(
            sample_transcript,
            version_number=1,
            created_by='test_user',
            change_note='Rolled back'
        )

        assert new_version == 3

        # Verify content matches version 1
        current = transcript_manager.get_transcript(sample_transcript)
        v1 = transcript_manager.get_transcript(sample_transcript, version=1)

        assert current['text'] == v1['text']
        assert len(current['segments']) == len(v1['segments'])

    @pytest.mark.unit
    @pytest.mark.fast
    def test_export_srt(self, transcript_manager, sample_transcript, tmp_path):
        """Test exporting transcript to SRT format."""
        output_file = tmp_path / "export.srt"

        content = transcript_manager.export_transcript(
            sample_transcript,
            format_name='srt',
            output_path=str(output_file)
        )

        assert output_file.exists()
        assert "1" in content
        assert "00:00:00,000 --> 00:00:05,000" in content

    @pytest.mark.unit
    @pytest.mark.fast
    def test_export_vtt(self, transcript_manager, sample_transcript, tmp_path):
        """Test exporting transcript to VTT format."""
        output_file = tmp_path / "export.vtt"

        content = transcript_manager.export_transcript(
            sample_transcript,
            format_name='vtt',
            output_path=str(output_file)
        )

        assert output_file.exists()
        assert content.startswith("WEBVTT")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_export_json(self, transcript_manager, sample_transcript, tmp_path):
        """Test exporting transcript to JSON format."""
        output_file = tmp_path / "export.json"

        content = transcript_manager.export_transcript(
            sample_transcript,
            format_name='json',
            output_path=str(output_file)
        )

        assert output_file.exists()
        data = json.loads(content)
        assert data['format'] == 'whisper-json'
        assert len(data['segments']) > 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_export_without_file(self, transcript_manager, sample_transcript):
        """Test exporting transcript without saving to file."""
        content = transcript_manager.export_transcript(
            sample_transcript,
            format_name='txt'
        )

        assert len(content) > 0
        assert "segment" in content

    @pytest.mark.unit
    @pytest.mark.fast
    def test_export_specific_version(self, transcript_manager, sample_transcript):
        """Test exporting specific version."""
        # Create version 2
        new_segments = [{"start": 0.0, "end": 5.0, "text": "Version 2"}]
        transcript_manager.update_transcript(
            sample_transcript,
            "Version 2",
            new_segments
        )

        # Export version 1
        content = transcript_manager.export_transcript(
            sample_transcript,
            format_name='txt',
            version=1
        )

        assert "first segment" in content
        assert "Version 2" not in content

    @pytest.mark.unit
    @pytest.mark.fast
    def test_delete_old_versions(self, transcript_manager, sample_transcript):
        """Test deleting old versions."""
        # Create several versions
        for i in range(5):
            segments = [{"start": 0.0, "end": 5.0, "text": f"Version {i+2}"}]
            transcript_manager.update_transcript(
                sample_transcript,
                f"Version {i+2}",
                segments
            )

        # Should have 6 versions total
        versions_before = transcript_manager.get_versions(sample_transcript)
        assert len(versions_before) == 6

        # Keep only 3 most recent
        deleted = transcript_manager.delete_old_versions(
            sample_transcript,
            keep_count=3
        )

        assert deleted == 3

        # Verify only 3 versions remain
        versions_after = transcript_manager.get_versions(sample_transcript)
        assert len(versions_after) == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_version_history(self, transcript_manager, sample_transcript):
        """Test getting complete version history."""
        # Create another version
        new_segments = [{"start": 0.0, "end": 5.0, "text": "Updated"}]
        transcript_manager.update_transcript(
            sample_transcript,
            "Updated",
            new_segments
        )

        history = transcript_manager.get_version_history(sample_transcript)

        assert history['transcript_id'] == sample_transcript
        assert history['version_count'] >= 2
        assert history['current_version'] is not None
        assert 'versions' in history
        assert 'exports' in history

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_transcript_by_job(self, transcript_manager, sample_transcript):
        """Test getting transcript by job ID."""
        # Get the transcript to find job_id
        transcript = transcript_manager.get_transcript(sample_transcript)
        job_id = transcript['job_id']

        # Get by job
        result = transcript_manager.get_transcript_by_job(job_id)

        assert result is not None
        assert result['id'] == sample_transcript

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_statistics(self, transcript_manager, sample_transcript):
        """Test getting transcript statistics."""
        # Create a few versions and exports
        new_segments = [{"start": 0.0, "end": 5.0, "text": "Updated"}]
        transcript_manager.update_transcript(
            sample_transcript,
            "Updated",
            new_segments
        )

        stats = transcript_manager.get_statistics()

        assert 'total_transcripts' in stats
        assert 'total_versions' in stats
        assert stats['total_transcripts'] >= 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestTranscriptWorkflow:
    """Test complete transcript workflow scenarios."""

    @pytest.mark.integration
    def test_complete_versioning_workflow(self, transcript_manager, sample_transcript, tmp_path):
        """Test complete workflow: create, update, compare, export, rollback."""
        # Step 1: Create initial transcript (already done by fixture)
        v1 = transcript_manager.get_transcript(sample_transcript)
        assert v1['version_number'] == 1

        # Step 2: Update transcript
        new_segments = [
            {"start": 0.0, "end": 8.0, "text": "Modified first part."},
            {"start": 8.0, "end": 15.0, "text": "Modified second part."}
        ]
        v2_num = transcript_manager.update_transcript(
            sample_transcript,
            "Modified first part. Modified second part.",
            new_segments,
            created_by='user1',
            change_note='Improved accuracy'
        )
        assert v2_num == 2

        # Step 3: Compare versions
        comparison = transcript_manager.compare_versions(sample_transcript, 1, 2)
        assert comparison['text_diff']['char_diff'] != 0

        # Step 4: Export both versions
        v1_srt = transcript_manager.export_transcript(
            sample_transcript,
            'srt',
            str(tmp_path / "v1.srt"),
            version=1
        )

        v2_srt = transcript_manager.export_transcript(
            sample_transcript,
            'srt',
            str(tmp_path / "v2.srt"),
            version=2
        )

        assert v1_srt != v2_srt

        # Step 5: Rollback to version 1
        v3_num = transcript_manager.rollback_to_version(
            sample_transcript,
            version_number=1,
            created_by='user1',
            change_note='Rollback to original'
        )
        assert v3_num == 3

        # Step 6: Verify current version matches v1
        current = transcript_manager.get_transcript(sample_transcript)
        assert current['text'] == v1['text']

        # Step 7: Check version history
        history = transcript_manager.get_version_history(sample_transcript)
        assert history['version_count'] == 3
        assert history['current_version'] == 3

    @pytest.mark.integration
    def test_multiple_format_export(self, transcript_manager, sample_transcript, tmp_path):
        """Test exporting to all supported formats."""
        formats = ['srt', 'vtt', 'json', 'txt', 'csv']

        for fmt in formats:
            output_file = tmp_path / f"export.{fmt}"
            content = transcript_manager.export_transcript(
                sample_transcript,
                fmt,
                str(output_file)
            )

            assert output_file.exists()
            assert len(content) > 0

            # Verify file content
            file_content = output_file.read_text(encoding='utf-8')
            assert file_content == content
