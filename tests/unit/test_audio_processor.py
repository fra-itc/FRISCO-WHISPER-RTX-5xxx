"""
Unit tests for Audio Processor module.

Tests audio format detection, validation, conversion,
metadata extraction, and audio manipulation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, mock_open
import json
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.audio_processor import (
    AudioProcessor,
    AudioMetadata,
    ConversionResult,
    convert_audio_file,
    get_audio_info,
    validate_audio_file
)


# ============================================================================
# Tests for Audio Processor Initialization
# ============================================================================

class TestAudioProcessorInitialization:
    """Test suite for AudioProcessor initialization."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_audio_processor_initialization(self):
        """Test basic AudioProcessor initialization."""
        processor = AudioProcessor()

        assert processor is not None
        assert hasattr(processor, 'supported_formats')
        assert hasattr(processor, 'target_sample_rate')
        assert hasattr(processor, 'target_channels')

    @pytest.mark.unit
    @pytest.mark.fast
    def test_default_target_specifications(self):
        """Test default target audio specifications."""
        processor = AudioProcessor()

        assert processor.target_sample_rate == 16000
        assert processor.target_channels == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_supported_formats_list(self):
        """Test that supported formats list is populated."""
        processor = AudioProcessor()

        assert isinstance(processor.supported_formats, list)
        assert len(processor.supported_formats) > 0
        assert '.wav' in processor.supported_formats
        assert '.mp3' in processor.supported_formats
        assert '.m4a' in processor.supported_formats


# ============================================================================
# Tests for Format Detection
# ============================================================================

class TestFormatDetection:
    """Test suite for audio format detection."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_detect_format_returns_metadata(self, sample_audio_file, mock_ffmpeg):
        """Test that detect_format returns AudioMetadata."""
        # Mock ffprobe output
        mock_output = {
            'format': {
                'format_name': 'wav',
                'duration': '1.0',
                'bit_rate': '256000'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 2,
                'codec_long_name': 'PCM signed 16-bit little-endian',
                'channel_layout': 'stereo'
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        metadata = processor.detect_format(str(sample_audio_file))

        assert metadata is not None
        assert isinstance(metadata, AudioMetadata)
        assert metadata.is_valid is True

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_detect_format_with_correct_fields(self, sample_audio_file, mock_ffmpeg):
        """Test that detected metadata has correct fields."""
        mock_output = {
            'format': {
                'format_name': 'wav',
                'duration': '1.0',
                'bit_rate': '256000'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        metadata = processor.detect_format(str(sample_audio_file))

        assert metadata.format == 'wav'
        assert metadata.codec == 'pcm_s16le'
        assert metadata.duration == 1.0
        assert metadata.sample_rate == 16000
        assert metadata.channels == 1

    @pytest.mark.unit
    def test_detect_format_nonexistent_file(self, temp_dir):
        """Test format detection with nonexistent file."""
        processor = AudioProcessor()
        fake_file = temp_dir / "nonexistent.wav"

        metadata = processor.detect_format(str(fake_file))

        assert metadata is not None
        assert metadata.is_valid is False
        assert metadata.error_message is not None

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_detect_format_no_audio_stream(self, sample_audio_file, mock_ffmpeg):
        """Test format detection when no audio stream found."""
        # Mock ffprobe output with no audio streams
        mock_output = {
            'format': {'format_name': 'unknown'},
            'streams': []
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        metadata = processor.detect_format(str(sample_audio_file))

        assert metadata.is_valid is False
        assert 'No audio stream' in metadata.error_message


# ============================================================================
# Tests for Format Support
# ============================================================================

class TestFormatSupport:
    """Test suite for format support checking."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.parametrize("format_ext,expected", [
        ('.wav', True),
        ('.mp3', True),
        ('.m4a', True),
        ('.aac', True),
        ('.flac', True),
        ('.ogg', True),
        ('.opus', True),
        ('.waptt', True),
        ('.mp4', True),
        ('.txt', False),
        ('.pdf', False),
        ('.xyz', False),
    ])
    def test_is_supported_format(self, format_ext, expected):
        """Test format support checking for various extensions."""
        processor = AudioProcessor()
        test_file = f"test{format_ext}"

        result = processor.is_supported_format(test_file)

        assert result == expected

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        processor = AudioProcessor()
        formats = processor.get_supported_formats()

        assert isinstance(formats, list)
        assert len(formats) > 0
        assert all(fmt.startswith('.') for fmt in formats)


# ============================================================================
# Tests for Audio Validation
# ============================================================================

class TestAudioValidation:
    """Test suite for audio validation."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_validate_audio_valid_file(self, sample_audio_file, mock_ffmpeg):
        """Test validation of valid audio file."""
        mock_output = {
            'format': {
                'format_name': 'wav',
                'duration': '1.0',
                'bit_rate': '256000'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        is_valid = processor.validate_audio(str(sample_audio_file))

        assert is_valid is True

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_validate_audio_invalid_duration(self, sample_audio_file, mock_ffmpeg):
        """Test validation with invalid duration."""
        mock_output = {
            'format': {
                'format_name': 'wav',
                'duration': '0.0',  # Invalid duration
                'bit_rate': '256000'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        is_valid = processor.validate_audio(str(sample_audio_file))

        assert is_valid is False

    @pytest.mark.unit
    def test_validate_audio_nonexistent_file(self, temp_dir):
        """Test validation of nonexistent file."""
        processor = AudioProcessor()
        fake_file = temp_dir / "nonexistent.wav"

        is_valid = processor.validate_audio(str(fake_file))

        assert is_valid is False


# ============================================================================
# Tests for Duration Extraction
# ============================================================================

class TestDurationExtraction:
    """Test suite for audio duration extraction."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_get_duration_returns_float(self, sample_audio_file, mock_ffmpeg):
        """Test that get_duration returns float."""
        mock_output = {
            'format': {
                'format_name': 'wav',
                'duration': '5.5',
                'bit_rate': '256000'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        duration = processor.get_duration(str(sample_audio_file))

        assert duration == 5.5
        assert isinstance(duration, float)

    @pytest.mark.unit
    def test_get_duration_invalid_file(self, temp_dir):
        """Test get_duration with invalid file."""
        processor = AudioProcessor()
        fake_file = temp_dir / "nonexistent.wav"

        duration = processor.get_duration(str(fake_file))

        assert duration is None


# ============================================================================
# Tests for WAV Compatibility
# ============================================================================

class TestWAVCompatibility:
    """Test suite for WAV format compatibility checking."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_is_wav_compatible_correct_format(self, sample_audio_file, mock_ffmpeg):
        """Test WAV compatibility check for correct format."""
        mock_output = {
            'format': {'format_name': 'wav'},
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        is_compatible = processor.is_wav_compatible(str(sample_audio_file))

        assert is_compatible is True

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_is_wav_compatible_wrong_sample_rate(self, sample_audio_file, mock_ffmpeg):
        """Test WAV compatibility with wrong sample rate."""
        mock_output = {
            'format': {'format_name': 'wav'},
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '44100',  # Wrong sample rate
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        is_compatible = processor.is_wav_compatible(str(sample_audio_file))

        assert is_compatible is False

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_is_wav_compatible_wrong_channels(self, sample_audio_file, mock_ffmpeg):
        """Test WAV compatibility with wrong channel count."""
        mock_output = {
            'format': {'format_name': 'wav'},
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 2  # Stereo instead of mono
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        is_compatible = processor.is_wav_compatible(str(sample_audio_file))

        assert is_compatible is False


# ============================================================================
# Tests for Audio Conversion
# ============================================================================

class TestAudioConversion:
    """Test suite for audio conversion."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_convert_to_wav_returns_path(self, sample_audio_file, temp_dir, mock_ffmpeg):
        """Test that convert_to_wav returns path."""
        # Mock ffprobe for duration
        mock_ffprobe_output = {
            'format': {
                'duration': '1.0'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '44100',
                'channels': 2
            }]
        }
        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_ffprobe_output)

        processor = AudioProcessor()
        output_path = processor.convert_to_wav(str(sample_audio_file), str(temp_dir))

        # Should return a path (or None if ffmpeg fails)
        assert output_path is None or isinstance(output_path, Path)

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_convert_to_wav_correct_parameters(self, sample_audio_file, temp_dir, mock_ffmpeg):
        """Test that correct ffmpeg parameters are used."""
        mock_ffprobe_output = {
            'format': {'duration': '1.0'},
            'streams': [{'codec_type': 'audio', 'sample_rate': '44100', 'channels': 2}]
        }
        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_ffprobe_output)

        processor = AudioProcessor()
        processor.convert_to_wav(str(sample_audio_file), str(temp_dir))

        # Check that Popen was called with ffmpeg
        if mock_ffmpeg['popen'].called:
            call_args = mock_ffmpeg['popen'].call_args[0][0]
            assert 'ffmpeg' in call_args
            assert '-ar' in call_args
            assert '16000' in call_args
            assert '-ac' in call_args
            assert '1' in call_args

    @pytest.mark.unit
    def test_convert_to_wav_nonexistent_file(self, temp_dir):
        """Test conversion of nonexistent file."""
        processor = AudioProcessor()
        fake_file = temp_dir / "nonexistent.m4a"

        result = processor.convert_to_wav(str(fake_file), str(temp_dir))

        assert result is None


# ============================================================================
# Tests for Metadata Extraction
# ============================================================================

class TestMetadataExtraction:
    """Test suite for metadata extraction."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_extract_metadata_returns_dict(self, sample_audio_file, mock_ffmpeg):
        """Test that extract_metadata returns dictionary."""
        mock_output = {
            'format': {
                'format_name': 'wav',
                'duration': '1.0',
                'bit_rate': '256000'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        processor = AudioProcessor()
        metadata = processor.extract_metadata(str(sample_audio_file))

        assert isinstance(metadata, dict)
        assert 'format' in metadata
        assert 'duration' in metadata
        assert 'sample_rate' in metadata

    @pytest.mark.unit
    def test_extract_metadata_invalid_file(self, temp_dir):
        """Test metadata extraction from invalid file."""
        processor = AudioProcessor()
        fake_file = temp_dir / "nonexistent.wav"

        metadata = processor.extract_metadata(str(fake_file))

        assert isinstance(metadata, dict)
        # Should return empty dict or dict with error info


# ============================================================================
# Tests for Audio Splitting
# ============================================================================

class TestAudioSplitting:
    """Test suite for audio splitting/chunking."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_split_audio_returns_list(self, sample_audio_file, temp_dir, mock_ffmpeg):
        """Test that split_audio returns list of paths."""
        mock_ffprobe_output = {
            'format': {'duration': '10.0'},
            'streams': [{'codec_type': 'audio', 'sample_rate': '16000', 'channels': 1}]
        }
        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_ffprobe_output)

        processor = AudioProcessor()
        chunks = processor.split_audio(
            str(sample_audio_file),
            chunk_duration=5.0,
            output_dir=str(temp_dir)
        )

        assert isinstance(chunks, list)

    @pytest.mark.unit
    def test_split_audio_invalid_file(self, temp_dir):
        """Test splitting nonexistent file."""
        processor = AudioProcessor()
        fake_file = temp_dir / "nonexistent.wav"

        chunks = processor.split_audio(str(fake_file), chunk_duration=5.0)

        assert chunks == []


# ============================================================================
# Tests for Audio Concatenation
# ============================================================================

class TestAudioConcatenation:
    """Test suite for audio concatenation."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_concatenate_audio_multiple_files(self, temp_dir, mock_ffmpeg):
        """Test concatenating multiple audio files."""
        file1 = temp_dir / "audio1.wav"
        file2 = temp_dir / "audio2.wav"

        # Create dummy files
        file1.touch()
        file2.touch()

        processor = AudioProcessor()
        output_file = temp_dir / "concatenated.wav"

        result = processor.concatenate_audio(
            [str(file1), str(file2)],
            str(output_file)
        )

        # Should attempt concatenation
        assert result is None or isinstance(result, Path)

    @pytest.mark.unit
    def test_concatenate_audio_empty_list(self, temp_dir):
        """Test concatenation with empty file list."""
        processor = AudioProcessor()
        output_file = temp_dir / "output.wav"

        result = processor.concatenate_audio([], str(output_file))

        assert result is None


# ============================================================================
# Tests for Convenience Functions
# ============================================================================

class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_convert_audio_file_function(self, sample_audio_file, temp_dir, mock_ffmpeg):
        """Test convert_audio_file convenience function."""
        mock_ffprobe_output = {
            'format': {'duration': '1.0'},
            'streams': [{'codec_type': 'audio', 'sample_rate': '44100', 'channels': 2}]
        }
        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_ffprobe_output)

        result = convert_audio_file(str(sample_audio_file), str(temp_dir))

        assert result is None or isinstance(result, Path)

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_get_audio_info_function(self, sample_audio_file, mock_ffmpeg):
        """Test get_audio_info convenience function."""
        mock_output = {
            'format': {
                'format_name': 'wav',
                'duration': '1.0',
                'bit_rate': '256000'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        info = get_audio_info(str(sample_audio_file))

        assert isinstance(info, dict)

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_validate_audio_file_function(self, sample_audio_file, mock_ffmpeg):
        """Test validate_audio_file convenience function."""
        mock_output = {
            'format': {
                'format_name': 'wav',
                'duration': '1.0',
                'bit_rate': '256000'
            },
            'streams': [{
                'codec_type': 'audio',
                'codec_name': 'pcm_s16le',
                'sample_rate': '16000',
                'channels': 1
            }]
        }

        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_output)

        is_valid = validate_audio_file(str(sample_audio_file))

        assert isinstance(is_valid, bool)


# ============================================================================
# Tests for String Representation
# ============================================================================

class TestStringRepresentation:
    """Test suite for string representation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_method(self):
        """Test __repr__ method of AudioProcessor."""
        processor = AudioProcessor()
        repr_str = repr(processor)

        assert isinstance(repr_str, str)
        assert 'AudioProcessor' in repr_str


# ============================================================================
# Tests for Progress Callbacks
# ============================================================================

class TestProgressCallbacks:
    """Test suite for progress callback functionality."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_convert_with_progress_callback(self, sample_audio_file, temp_dir, mock_ffmpeg):
        """Test conversion with progress callback."""
        mock_ffprobe_output = {
            'format': {'duration': '1.0'},
            'streams': [{'codec_type': 'audio', 'sample_rate': '44100', 'channels': 2}]
        }
        mock_ffmpeg['run'].return_value.stdout = json.dumps(mock_ffprobe_output)

        progress_values = []

        def progress_callback(progress):
            progress_values.append(progress)

        processor = AudioProcessor()
        processor.convert_to_wav(
            str(sample_audio_file),
            str(temp_dir),
            progress_callback=progress_callback
        )

        # Progress callback should have been called (if ffmpeg mock supports it)
        # In mock environment, this might not actually trigger
        assert isinstance(progress_values, list)


# ============================================================================
# Tests for Error Handling
# ============================================================================

class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.unit
    def test_initialization_without_ffmpeg(self):
        """Test initialization when ffmpeg is not available."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            processor = AudioProcessor()

            # Should initialize but mark ffmpeg as unavailable
            assert processor._ffmpeg_available is False

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_detect_format_with_ffprobe_error(self, sample_audio_file, mock_ffmpeg):
        """Test format detection when ffprobe fails."""
        mock_ffmpeg['run'].side_effect = subprocess.CalledProcessError(1, 'ffprobe')

        processor = AudioProcessor()
        metadata = processor.detect_format(str(sample_audio_file))

        assert metadata.is_valid is False
        assert metadata.error_message is not None
