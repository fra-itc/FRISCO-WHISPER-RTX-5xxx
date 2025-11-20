"""
Pytest fixtures and configuration for Frisco Whisper RTX testing framework.

This module provides reusable fixtures for testing the transcription application,
including mocked GPU resources, sample audio files, and database fixtures.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest
import sqlite3
import wave
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Session-level fixtures (setup once per test session)
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture providing path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_audio_file(test_data_dir):
    """
    Fixture providing path to test audio file.

    Creates a minimal valid WAV file for testing if it doesn't exist.
    This is a 1-second silent audio file at 16kHz mono.

    Returns:
        Path: Path to the test audio file
    """
    audio_path = test_data_dir / "sample_audio.wav"
    test_data_dir.mkdir(parents=True, exist_ok=True)

    if not audio_path.exists():
        # Generate 1 second of silence at 16kHz, 16-bit mono
        sample_rate = 16000
        duration = 1.0  # seconds
        num_samples = int(sample_rate * duration)

        # Create silent audio (zeros)
        audio_data = np.zeros(num_samples, dtype=np.int16)

        # Write WAV file
        with wave.open(str(audio_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

    return audio_path


@pytest.fixture(scope="session")
def sample_m4a_file(test_data_dir):
    """
    Fixture providing path to test M4A file.

    Note: This is a placeholder. In production, you should use a real M4A file.
    For now, this returns the path where an M4A file should be placed.

    Returns:
        Path: Path where test M4A file should exist
    """
    m4a_path = test_data_dir / "sample_audio.m4a"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    return m4a_path


# ============================================================================
# Function-level fixtures (setup per test function)
# ============================================================================

@pytest.fixture
def temp_dir():
    """
    Fixture providing a temporary directory for test outputs.

    Automatically cleaned up after test completion.

    Yields:
        Path: Path to temporary directory
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def temp_db(temp_dir):
    """
    Fixture providing a temporary SQLite database for testing.

    Creates a simple transcriptions table for testing database operations.

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        Path: Path to temporary database file
    """
    db_path = temp_dir / "test_transcriptions.db"

    # Create database with schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_path TEXT NOT NULL,
            transcript_path TEXT,
            language TEXT,
            model_size TEXT,
            compute_type TEXT,
            duration_seconds REAL,
            processing_time REAL,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup is handled by temp_dir fixture


@pytest.fixture
def mock_gpu():
    """
    Fixture to mock GPU availability and operations.

    Provides a mock torch module with CUDA support enabled.

    Yields:
        Mock: Mocked torch module with GPU capabilities
    """
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA RTX 5080 (Mocked)"
    mock_torch.cuda.get_device_properties.return_value = MagicMock(
        total_memory=16 * 1024**3  # 16 GB
    )
    mock_torch.version.cuda = "12.1"

    with patch.dict('sys.modules', {'torch': mock_torch}):
        yield mock_torch


@pytest.fixture
def mock_gpu_unavailable():
    """
    Fixture to mock GPU unavailability (CPU-only mode).

    Yields:
        Mock: Mocked torch module with CUDA disabled
    """
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False

    with patch.dict('sys.modules', {'torch': mock_torch}):
        yield mock_torch


@pytest.fixture
def mock_whisper_model():
    """
    Fixture providing a mocked WhisperModel for testing.

    Simulates the faster_whisper.WhisperModel with transcribe functionality.

    Yields:
        Mock: Mocked WhisperModel instance
    """
    mock_model = MagicMock()

    # Mock transcription result
    mock_segment = MagicMock()
    mock_segment.start = 0.0
    mock_segment.end = 1.0
    mock_segment.text = "This is a test transcription"

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.95

    mock_model.transcribe.return_value = ([mock_segment], mock_info)

    yield mock_model


@pytest.fixture
def transcription_engine(mock_gpu, mock_whisper_model):
    """
    Fixture providing an initialized transcription engine for testing.

    Combines GPU mocking and Whisper model mocking to provide a complete
    transcription engine setup.

    Args:
        mock_gpu: GPU mocking fixture
        mock_whisper_model: Whisper model mocking fixture

    Yields:
        dict: Dictionary containing mocked components
    """
    with patch('faster_whisper.WhisperModel', return_value=mock_whisper_model):
        yield {
            'model': mock_whisper_model,
            'gpu': mock_gpu,
            'device': 'cuda',
            'compute_type': 'float16'
        }


@pytest.fixture
def mock_ffmpeg():
    """
    Fixture to mock ffmpeg subprocess calls.

    Prevents actual ffmpeg execution during tests.

    Yields:
        Mock: Mocked subprocess module
    """
    with patch('subprocess.run') as mock_run, \
         patch('subprocess.Popen') as mock_popen, \
         patch('subprocess.check_call') as mock_check_call:

        # Mock successful ffmpeg execution
        mock_run.return_value = MagicMock(returncode=0, stdout="1.0", stderr="")

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = iter(["out_time_us=1000000\n"])
        mock_process.stderr.read.return_value = ""
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        yield {
            'run': mock_run,
            'popen': mock_popen,
            'check_call': mock_check_call
        }


@pytest.fixture
def sample_transcription_result():
    """
    Fixture providing sample transcription result data.

    Returns:
        dict: Sample transcription result with segments and metadata
    """
    return {
        'segments': [
            {
                'id': 0,
                'start': 0.0,
                'end': 2.5,
                'text': 'Hello, this is a test.',
            },
            {
                'id': 1,
                'start': 2.5,
                'end': 5.0,
                'text': 'This is the second segment.',
            },
        ],
        'language': 'en',
        'language_probability': 0.95,
        'duration': 5.0,
    }


@pytest.fixture
def sample_srt_content():
    """
    Fixture providing sample SRT subtitle content.

    Returns:
        str: Sample SRT formatted subtitle content
    """
    return """1
00:00:00,000 --> 00:00:02,500
Hello, this is a test.

2
00:00:02,500 --> 00:00:05,000
This is the second segment.

"""


# ============================================================================
# Utility fixtures
# ============================================================================

@pytest.fixture
def capture_colors():
    """
    Fixture to capture and test colored console output.

    Yields:
        Mock: Mocked print function that captures colored output
    """
    with patch('builtins.print') as mock_print:
        yield mock_print


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Fixture to reset global state between tests.

    Automatically runs before each test to ensure clean state.
    """
    # Reset any global variables if needed
    yield
    # Cleanup after test


# ============================================================================
# Parametrize helpers
# ============================================================================

def pytest_configure(config):
    """
    Configure pytest with custom settings.

    This runs once at the start of the test session.
    """
    config.addinivalue_line(
        "markers", "requires_ffmpeg: mark test as requiring ffmpeg binary"
    )
    config.addinivalue_line(
        "markers", "requires_model: mark test as requiring actual Whisper model"
    )


# ============================================================================
# Test data generators
# ============================================================================

def generate_test_audio_samples():
    """
    Generator for various test audio configurations.

    Yields:
        tuple: (sample_rate, duration, description)
    """
    yield (16000, 1.0, "1 second at 16kHz")
    yield (16000, 5.0, "5 seconds at 16kHz")
    yield (44100, 1.0, "1 second at 44.1kHz")
    yield (48000, 2.0, "2 seconds at 48kHz")


def generate_model_configs():
    """
    Generator for various model configurations to test.

    Yields:
        dict: Model configuration parameters
    """
    models = ['small', 'medium', 'large-v3']
    compute_types = ['float16', 'float32', 'int8']
    devices = ['cuda', 'cpu']

    for model in models:
        for compute in compute_types:
            for device in devices:
                if device == 'cpu' and compute in ['float16', 'int8']:
                    continue  # Skip invalid combinations
                yield {
                    'model_size': model,
                    'compute_type': compute,
                    'device': device
                }
