"""
Frisco Whisper RTX - Core Transcription Module

This module provides a modular, reusable transcription engine
powered by Faster-Whisper with GPU optimization for NVIDIA RTX cards.

Main Classes:
    - TranscriptionEngine: Core transcription engine
    - GPUManager: GPU detection and management
    - AudioProcessor: Audio format detection and conversion
    - AudioConverter: Audio format conversion utilities (legacy)
    - TranscriptionResult: Result dataclass
    - GPUInfo: GPU information dataclass

Quick Start:
    from src.core import TranscriptionEngine

    # Basic usage
    engine = TranscriptionEngine(model_size='large-v3')
    result = engine.transcribe('audio.wav', language='it')

    # With context manager (auto cleanup)
    with TranscriptionEngine(model_size='large-v3') as engine:
        result = engine.transcribe('audio.wav')

    # Simple convenience function
    from src.core import transcribe_file
    result = transcribe_file('audio.wav', model_size='large-v3', language='it')

    # GPU Management
    from src.core import GPUManager
    gpu_mgr = GPUManager()
    gpu_mgr.print_gpu_summary()

    # Audio Processing
    from src.core import AudioProcessor
    processor = AudioProcessor()
    metadata = processor.detect_format('audio.m4a')
    wav_path = processor.convert_to_wav('audio.m4a')
"""

from .transcription import (
    TranscriptionEngine,
    AudioConverter,
    TranscriptionResult,
    GPUInfo,
    transcribe_file,
    test_gpu
)

from .gpu_manager import (
    GPUManager,
    GPUInfo as GPUManagerInfo,
    MemoryInfo,
    get_default_device,
    get_recommended_compute_type,
    print_gpu_info,
    test_gpu_available
)

from .audio_processor import (
    AudioProcessor,
    AudioMetadata,
    ConversionResult,
    convert_audio_file,
    get_audio_info,
    validate_audio_file
)

from .transcription_service import (
    TranscriptionService,
    TranscriptionServiceError
)

__version__ = '2.0.0'
__author__ = 'Frisco'
__all__ = [
    # Transcription
    'TranscriptionEngine',
    'AudioConverter',
    'TranscriptionResult',
    'GPUInfo',
    'transcribe_file',
    'test_gpu',
    # GPU Management
    'GPUManager',
    'GPUManagerInfo',
    'MemoryInfo',
    'get_default_device',
    'get_recommended_compute_type',
    'print_gpu_info',
    'test_gpu_available',
    # Audio Processing
    'AudioProcessor',
    'AudioMetadata',
    'ConversionResult',
    'convert_audio_file',
    'get_audio_info',
    'validate_audio_file',
    # Integrated Service
    'TranscriptionService',
    'TranscriptionServiceError'
]
