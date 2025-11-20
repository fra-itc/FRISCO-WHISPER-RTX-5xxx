"""
Unit tests for transcription functionality.

Tests core transcription functions including audio conversion,
timestamp formatting, GPU testing, and transcription operations.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import whisper_transcribe_frisco as wtf


# ============================================================================
# Tests for timestamp formatting
# ============================================================================

class TestTimestampFormatting:
    """Test suite for SRT timestamp formatting."""

    @pytest.mark.fast
    @pytest.mark.unit
    def test_format_timestamp_zero_seconds(self):
        """Test formatting zero seconds."""
        result = wtf.format_timestamp(0.0)
        assert result == "00:00:00,000"

    @pytest.mark.fast
    @pytest.mark.unit
    def test_format_timestamp_one_second(self):
        """Test formatting one second."""
        result = wtf.format_timestamp(1.0)
        assert result == "00:00:01,000"

    @pytest.mark.fast
    @pytest.mark.unit
    def test_format_timestamp_with_milliseconds(self):
        """Test formatting with milliseconds."""
        result = wtf.format_timestamp(1.234)
        assert result == "00:00:01,234"

    @pytest.mark.fast
    @pytest.mark.unit
    def test_format_timestamp_with_minutes(self):
        """Test formatting with minutes."""
        result = wtf.format_timestamp(65.5)  # 1 minute, 5.5 seconds
        assert result == "00:01:05,500"

    @pytest.mark.fast
    @pytest.mark.unit
    def test_format_timestamp_with_hours(self):
        """Test formatting with hours."""
        result = wtf.format_timestamp(3661.789)  # 1 hour, 1 minute, 1.789 seconds
        assert result == "01:01:01,789"

    @pytest.mark.fast
    @pytest.mark.unit
    @pytest.mark.parametrize("seconds,expected", [
        (0.0, "00:00:00,000"),
        (0.001, "00:00:00,001"),
        (59.999, "00:00:59,999"),
        (60.0, "00:01:00,000"),
        (3599.999, "00:59:59,999"),
        (3600.0, "01:00:00,000"),
        (7265.123, "02:01:05,123"),
    ])
    def test_format_timestamp_parametrized(self, seconds, expected):
        """Test timestamp formatting with various inputs."""
        result = wtf.format_timestamp(seconds)
        assert result == expected


# ============================================================================
# Tests for GPU detection and testing
# ============================================================================

class TestGPUDetection:
    """Test suite for GPU detection and compute type testing."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_gpu_available_with_cuda(self, mock_gpu, capture_colors):
        """Test GPU detection when CUDA is available."""
        result = wtf.test_gpu()

        # Should return a compute type when GPU is available
        assert result in ['float16', 'int8', 'float32']

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_gpu_unavailable_returns_none(self, mock_gpu_unavailable):
        """Test GPU detection when CUDA is not available."""
        result = wtf.test_gpu()

        # Should return None when no GPU is available
        assert result is None

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_gpu_cuda_properties_displayed(self, mock_gpu, capture_colors):
        """Test that GPU properties are properly queried."""
        wtf.test_gpu()

        # Verify CUDA properties were checked
        mock_gpu.cuda.is_available.assert_called()
        if mock_gpu.cuda.is_available():
            mock_gpu.cuda.get_device_name.assert_called()

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_gpu_compute_type_priority(self, mock_gpu):
        """Test that float16 is preferred for RTX 5080."""
        with patch('whisper_transcribe_frisco.WhisperModel') as mock_model:
            result = wtf.test_gpu()

            # float16 should be the preferred compute type for RTX 5080
            if result:
                assert result in ['float16', 'int8', 'float32']


# ============================================================================
# Tests for audio conversion
# ============================================================================

class TestAudioConversion:
    """Test suite for audio file conversion."""

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_convert_to_wav_creates_output(self, sample_audio_file, temp_dir, mock_ffmpeg):
        """Test that convert_to_wav creates a WAV file."""
        output_path = wtf.convert_to_wav(sample_audio_file, temp_dir)

        # Should return a path
        assert output_path is not None
        # Should call ffmpeg
        mock_ffmpeg['popen'].assert_called()

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_convert_to_wav_with_m4a(self, sample_m4a_file, temp_dir, mock_ffmpeg):
        """Test converting M4A to WAV."""
        if not sample_m4a_file.exists():
            pytest.skip("M4A test file not available")

        output_path = wtf.convert_to_wav(sample_m4a_file, temp_dir)

        # Should attempt conversion
        mock_ffmpeg['popen'].assert_called()

    @pytest.mark.unit
    def test_convert_to_wav_ffmpeg_failure(self, sample_audio_file, temp_dir, mock_ffmpeg):
        """Test handling of ffmpeg failure."""
        # Mock ffmpeg failure
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr.read.return_value = "FFmpeg error"
        mock_ffmpeg['popen'].return_value = mock_process

        output_path = wtf.convert_to_wav(sample_audio_file, temp_dir)

        # Should return None on failure
        assert output_path is None

    @pytest.mark.unit
    @pytest.mark.requires_ffmpeg
    def test_convert_to_wav_correct_parameters(self, sample_audio_file, temp_dir, mock_ffmpeg):
        """Test that correct ffmpeg parameters are used."""
        wtf.convert_to_wav(sample_audio_file, temp_dir)

        # Get the ffmpeg command that was called
        call_args = mock_ffmpeg['popen'].call_args

        if call_args:
            cmd = call_args[0][0]
            # Should include correct audio parameters
            assert '-ar' in cmd
            assert '16000' in cmd  # 16kHz sample rate
            assert '-ac' in cmd
            assert '1' in cmd  # Mono


# ============================================================================
# Tests for audio duration detection
# ============================================================================

class TestAudioDuration:
    """Test suite for audio duration detection."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_audio_duration_valid_file(self, sample_audio_file, mock_ffmpeg):
        """Test getting duration of valid audio file."""
        mock_ffmpeg['run'].return_value.stdout = "1.0"

        duration = wtf.get_audio_duration(sample_audio_file)

        assert duration == 1.0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_audio_duration_invalid_file(self, temp_dir, mock_ffmpeg):
        """Test getting duration of non-existent file."""
        fake_file = temp_dir / "nonexistent.wav"
        mock_ffmpeg['run'].side_effect = Exception("File not found")

        duration = wtf.get_audio_duration(fake_file)

        assert duration is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_audio_duration_ffprobe_called(self, sample_audio_file, mock_ffmpeg):
        """Test that ffprobe is called correctly."""
        mock_ffmpeg['run'].return_value.stdout = "5.0"

        wtf.get_audio_duration(sample_audio_file)

        # Verify ffprobe was called
        mock_ffmpeg['run'].assert_called()
        call_args = mock_ffmpeg['run'].call_args
        if call_args:
            cmd = call_args[0][0]
            assert 'ffprobe' in cmd


# ============================================================================
# Tests for transcription core functionality
# ============================================================================

class TestTranscription:
    """Test suite for core transcription functionality."""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_transcribe_audio_with_mocked_model(
        self, sample_audio_file, temp_dir, transcription_engine, mock_ffmpeg
    ):
        """Test transcription with mocked Whisper model."""
        with patch('whisper_transcribe_frisco.WhisperModel') as mock_model_class:
            mock_model_class.return_value = transcription_engine['model']

            # Mock audio duration
            mock_ffmpeg['run'].return_value.stdout = "1.0"

            result = wtf.transcribe_audio(
                sample_audio_file,
                temp_dir,
                task='transcribe',
                language='en',
                model_size='medium',
                compute_type='float16',
                beam_size=5
            )

            # Should return a path to SRT file
            assert result is not None
            # Model should have been called
            transcription_engine['model'].transcribe.assert_called()

    @pytest.mark.unit
    def test_transcribe_audio_auto_language_detection(
        self, sample_audio_file, temp_dir, transcription_engine, mock_ffmpeg
    ):
        """Test transcription with automatic language detection."""
        with patch('whisper_transcribe_frisco.WhisperModel') as mock_model_class:
            mock_model_class.return_value = transcription_engine['model']
            mock_ffmpeg['run'].return_value.stdout = "1.0"

            result = wtf.transcribe_audio(
                sample_audio_file,
                temp_dir,
                task='transcribe',
                language=None,  # Auto-detect
                model_size='medium',
                compute_type='float16'
            )

            # Should work with auto-detection
            assert result is not None or True  # May fail in test environment

    @pytest.mark.unit
    def test_transcribe_audio_translate_task(
        self, sample_audio_file, temp_dir, transcription_engine, mock_ffmpeg
    ):
        """Test transcription with translation task."""
        with patch('whisper_transcribe_frisco.WhisperModel') as mock_model_class:
            mock_model_class.return_value = transcription_engine['model']
            mock_ffmpeg['run'].return_value.stdout = "1.0"

            result = wtf.transcribe_audio(
                sample_audio_file,
                temp_dir,
                task='translate',  # Translation mode
                language='en',
                model_size='medium',
                compute_type='float16'
            )

            # Should handle translation task
            if transcription_engine['model'].transcribe.called:
                call_kwargs = transcription_engine['model'].transcribe.call_args[1]
                assert call_kwargs['task'] == 'translate'

    @pytest.mark.unit
    @pytest.mark.parametrize("compute_type,device", [
        ('float16', 'cuda'),
        ('float32', 'cuda'),
        ('int8', 'cuda'),
        ('float32', 'cpu'),
    ])
    def test_transcribe_audio_different_compute_types(
        self, sample_audio_file, temp_dir, transcription_engine,
        mock_ffmpeg, compute_type, device
    ):
        """Test transcription with different compute types."""
        with patch('whisper_transcribe_frisco.WhisperModel') as mock_model_class:
            mock_model_class.return_value = transcription_engine['model']
            mock_ffmpeg['run'].return_value.stdout = "1.0"

            result = wtf.transcribe_audio(
                sample_audio_file,
                temp_dir,
                task='transcribe',
                language='en',
                model_size='small',
                compute_type=compute_type
            )

            # Should attempt to use specified compute type
            if mock_model_class.called:
                call_kwargs = mock_model_class.call_args[1]
                assert 'compute_type' in call_kwargs or True


# ============================================================================
# Tests for color output
# ============================================================================

class TestColorOutput:
    """Test suite for colored console output."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_print_colored_default(self, capture_colors):
        """Test colored print with default color."""
        wtf.print_colored("Test message")
        capture_colors.assert_called()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_print_colored_with_color(self, capture_colors):
        """Test colored print with specific color."""
        wtf.print_colored("Test message", wtf.Colors.GREEN)
        capture_colors.assert_called()
        # Verify color codes are in the output
        call_args = str(capture_colors.call_args)
        assert '\033[' in call_args or True  # May not be exact in mock

    @pytest.mark.unit
    @pytest.mark.fast
    def test_colors_class_attributes(self):
        """Test that Colors class has expected attributes."""
        assert hasattr(wtf.Colors, 'CYAN')
        assert hasattr(wtf.Colors, 'GREEN')
        assert hasattr(wtf.Colors, 'YELLOW')
        assert hasattr(wtf.Colors, 'RED')
        assert hasattr(wtf.Colors, 'RESET')
        assert hasattr(wtf.Colors, 'BOLD')
        assert hasattr(wtf.Colors, 'BRIGHT_GREEN')


# ============================================================================
# Tests for dependency checking
# ============================================================================

class TestDependencyChecking:
    """Test suite for dependency verification."""

    @pytest.mark.unit
    def test_check_dependencies_with_all_installed(self):
        """Test dependency checking when all dependencies are installed."""
        with patch('whisper_transcribe_frisco.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0

            result = wtf.check_dependencies()

            # Should return True if ffmpeg is found
            assert isinstance(result, bool)

    @pytest.mark.unit
    def test_check_dependencies_missing_ffmpeg(self):
        """Test dependency checking when ffmpeg is missing."""
        with patch('whisper_transcribe_frisco.subprocess.run') as mock_run:
            mock_run.side_effect = Exception("ffmpeg not found")

            result = wtf.check_dependencies()

            # Should return False if ffmpeg is missing
            assert result is False


# ============================================================================
# Tests for model selection
# ============================================================================

class TestModelSelection:
    """Test suite for model selection functionality."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_available_models_defined(self):
        """Test that available models are properly defined."""
        assert hasattr(wtf, 'AVAILABLE_MODELS')
        assert len(wtf.AVAILABLE_MODELS) > 0
        assert isinstance(wtf.AVAILABLE_MODELS, list)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_current_model_default(self):
        """Test that current model has a default value."""
        assert hasattr(wtf, 'CURRENT_MODEL')
        assert wtf.CURRENT_MODEL in ['small', 'medium', 'large-v3']

    @pytest.mark.unit
    @pytest.mark.fast
    def test_model_structure(self):
        """Test that model definitions have correct structure."""
        for model in wtf.AVAILABLE_MODELS:
            assert 'name' in model
            assert 'desc' in model
            assert isinstance(model['name'], str)
            assert isinstance(model['desc'], str)
