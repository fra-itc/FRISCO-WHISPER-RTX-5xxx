#!/usr/bin/env python3
"""
TranscriptionEngine - Core Whisper transcription logic
Modular, reusable transcription engine with GPU optimization
"""

import os
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

# Import new modular components
from .gpu_manager import GPUManager, GPUInfo as GPUManagerInfo
from .audio_processor import AudioProcessor, AudioMetadata


@dataclass
class TranscriptionResult:
    """Result of a transcription operation"""
    success: bool
    output_path: Optional[Path] = None
    segments_count: int = 0
    language: Optional[str] = None
    language_probability: float = 0.0
    duration: float = 0.0
    error: Optional[str] = None


@dataclass
class GPUInfo:
    """GPU information and capabilities (legacy - use gpu_manager.GPUInfo)"""
    available: bool
    device_name: Optional[str] = None
    vram_gb: float = 0.0
    cuda_version: Optional[str] = None
    supported_compute_types: List[str] = None
    recommended_compute_type: Optional[str] = None


class TranscriptionEngine:
    """
    Core transcription engine using Faster-Whisper.

    Features:
    - Automatic GPU detection and optimization
    - Multiple compute type support (float16, float32, int8)
    - Automatic fallback on errors
    - Progress callbacks for real-time updates
    - Configurable model sizes
    - VAD (Voice Activity Detection) filtering

    Example:
        engine = TranscriptionEngine(model_size='large-v3')
        result = engine.transcribe('audio.wav', language='it')
        if result.success:
            print(f"Transcription saved to: {result.output_path}")
    """

    AVAILABLE_MODELS = ['tiny', 'base', 'small', 'medium', 'large-v3', 'large-v2', 'large']

    def __init__(
        self,
        model_size: str = 'large-v3',
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        auto_detect_gpu: bool = True,
        device_index: Optional[int] = None
    ):
        """
        Initialize TranscriptionEngine.

        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3')
            device: Device to use ('cuda' or 'cpu'). Auto-detected if None.
            compute_type: Compute type ('float16', 'float32', 'int8'). Auto-detected if None.
            auto_detect_gpu: Automatically detect and configure GPU settings
            device_index: Specific GPU device index to use (for multi-GPU systems)
        """
        if model_size not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid model size. Choose from: {self.AVAILABLE_MODELS}")

        self.model_size = model_size
        self.model = None
        self.gpu_info = None
        self.device_index = device_index

        # Initialize GPU manager and audio processor
        self.gpu_manager = GPUManager()
        self.audio_processor = AudioProcessor()

        # Auto-detect GPU capabilities using GPU manager
        if auto_detect_gpu:
            self.gpu_info = self._detect_gpu()
            self.device = device or ('cuda' if self.gpu_info.available else 'cpu')
            self.compute_type = compute_type or self.gpu_info.recommended_compute_type or 'float32'

            # Auto-select best GPU if not specified
            if self.device == 'cuda' and self.device_index is None:
                self.device_index = self.gpu_manager.select_best_gpu()
        else:
            self.device = device or 'cpu'
            self.compute_type = compute_type or 'float32'

    def _detect_gpu(self) -> GPUInfo:
        """
        Detect GPU capabilities and recommend optimal compute type.
        Uses the new GPUManager module.

        Returns:
            GPUInfo object with GPU details and recommendations (legacy format)
        """
        try:
            # Use GPU manager for detection
            device_id = self.device_index if self.device_index is not None else 0

            if not self.gpu_manager.has_cuda:
                return GPUInfo(available=False)

            # Get GPU info from manager
            gpu_info = self.gpu_manager.get_gpu_info(device_id)

            if not gpu_info:
                return GPUInfo(available=False)

            # Convert to legacy GPUInfo format
            return GPUInfo(
                available=True,
                device_name=gpu_info.name,
                vram_gb=gpu_info.total_memory_gb,
                cuda_version=gpu_info.cuda_version,
                supported_compute_types=gpu_info.supported_compute_types,
                recommended_compute_type=gpu_info.recommended_compute_type
            )

        except Exception as e:
            return GPUInfo(available=False)

    def load_model(self) -> bool:
        """
        Load the Whisper model with automatic fallback.
        Uses GPU manager's fallback strategies.

        Returns:
            True if model loaded successfully, False otherwise
        """
        from faster_whisper import WhisperModel

        # Try primary configuration
        try:
            model_kwargs = {
                'model_size_or_path': self.model_size,
                'device': self.device,
                'compute_type': self.compute_type
            }

            # Add device index for CUDA
            if self.device == 'cuda' and self.device_index is not None:
                model_kwargs['device_index'] = self.device_index

            self.model = WhisperModel(**model_kwargs)
            return True
        except Exception as e:
            print(f"[WARN] Primary config failed ({self.device}/{self.compute_type}): {e}")

        # Try fallback configurations from GPU manager
        fallback_configs = self.gpu_manager.get_fallback_configs()

        for config in fallback_configs:
            try:
                model_kwargs = {
                    'model_size_or_path': self.model_size,
                    'device': config['device'],
                    'compute_type': config['compute']
                }

                # Add device index for CUDA fallbacks
                if config['device'] == 'cuda' and self.device_index is not None:
                    model_kwargs['device_index'] = self.device_index

                self.model = WhisperModel(**model_kwargs)
                self.device = config['device']
                self.compute_type = config['compute']
                print(f"[OK] Fallback successful: {self.device}/{self.compute_type}")
                return True
            except Exception:
                continue

        return False

    def transcribe(
        self,
        audio_path: str,
        output_dir: Optional[str] = None,
        task: str = 'transcribe',
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        progress_callback: Optional[Callable[[dict], None]] = None,
        word_timestamps: bool = False
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (WAV format recommended)
            output_dir: Directory to save output SRT file. Uses audio_path dir if None.
            task: 'transcribe' (maintain language) or 'translate' (to English)
            language: Language code ('it', 'en', etc.) or None for auto-detection
            beam_size: Beam size for decoding (higher = more accurate but slower)
            vad_filter: Enable Voice Activity Detection filtering
            progress_callback: Optional callback function for progress updates
                               Receives dict with: segment_number, text, start, end, progress_pct
            word_timestamps: Enable word-level timestamps

        Returns:
            TranscriptionResult with success status and details
        """
        start_time = time.time()
        audio_path = Path(audio_path)

        if not audio_path.exists():
            return TranscriptionResult(
                success=False,
                error=f"Audio file not found: {audio_path}"
            )

        # Load model if not already loaded
        if self.model is None:
            if not self.load_model():
                return TranscriptionResult(
                    success=False,
                    error="Failed to load model with all fallback configurations"
                )

        # Determine output path
        if output_dir is None:
            output_dir = audio_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{audio_path.stem}.srt"

        # Get audio duration for progress tracking using audio processor
        audio_duration = self.audio_processor.get_duration(str(audio_path))

        # Prepare transcription parameters
        transcribe_params = {
            'audio': str(audio_path),
            'task': task,
            'beam_size': beam_size,
            'vad_filter': vad_filter,
            'word_timestamps': word_timestamps,
            'condition_on_previous_text': True,
            'temperature': 0.0,
            'compression_ratio_threshold': 2.4,
            'log_prob_threshold': -1.0,
            'no_speech_threshold': 0.6
        }

        if vad_filter:
            transcribe_params['vad_parameters'] = dict(min_silence_duration_ms=500)

        # Add language only if specified (None = auto-detect)
        if language is not None:
            transcribe_params['language'] = language

        try:
            # Perform transcription
            segments, info = self.model.transcribe(**transcribe_params)

            # Process and save segments
            segments_list = []
            segment_count = 0

            with open(output_path, 'w', encoding='utf-8') as f:
                for segment in segments:
                    segment_count += 1
                    segments_list.append(segment)

                    # Write SRT format
                    f.write(f"{segment_count}\n")
                    f.write(f"{self._format_timestamp(segment.start)} --> {self._format_timestamp(segment.end)}\n")
                    f.write(f"{segment.text.strip()}\n\n")
                    f.flush()

                    # Progress callback
                    if progress_callback:
                        progress_data = {
                            'segment_number': segment_count,
                            'text': segment.text.strip(),
                            'start': segment.start,
                            'end': segment.end,
                            'progress_pct': (segment.end / audio_duration * 100) if audio_duration else 0,
                            'audio_duration': audio_duration
                        }
                        progress_callback(progress_data)

            duration = time.time() - start_time

            return TranscriptionResult(
                success=True,
                output_path=output_path,
                segments_count=segment_count,
                language=info.language,
                language_probability=info.language_probability,
                duration=duration
            )

        except Exception as e:
            return TranscriptionResult(
                success=False,
                error=f"Transcription failed: {str(e)}"
            )

    def transcribe_with_retry(
        self,
        audio_path: str,
        max_retries: int = 3,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe with automatic retry on failure.

        Args:
            audio_path: Path to audio file
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments passed to transcribe()

        Returns:
            TranscriptionResult
        """
        for attempt in range(max_retries):
            result = self.transcribe(audio_path, **kwargs)

            if result.success:
                return result

            if attempt < max_retries - 1:
                print(f"[RETRY {attempt + 1}/{max_retries}] Retrying transcription...")
                time.sleep(2)  # Wait before retry

        return result

    def get_gpu_info(self) -> Optional[GPUInfo]:
        """Get GPU information and capabilities."""
        return self.gpu_info

    def cleanup(self):
        """Clean up resources and free memory."""
        if self.model is not None:
            del self.model
            self.model = None

        # Clear CUDA cache using GPU manager
        if self.device == 'cuda':
            self.gpu_manager.clear_cache(self.device_index)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format timestamp for SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def __enter__(self):
        """Context manager entry."""
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

    def __repr__(self) -> str:
        """String representation."""
        return (f"TranscriptionEngine(model={self.model_size}, "
                f"device={self.device}, compute={self.compute_type})")


class AudioConverter:
    """
    Audio conversion utilities for preparing files for transcription.
    Converts various audio formats to WAV 16kHz mono.

    Note: This class is now a wrapper around AudioProcessor for backward compatibility.
    Use AudioProcessor directly for new code.
    """

    def __init__(self):
        """Initialize AudioConverter with AudioProcessor."""
        self._processor = AudioProcessor()

    @staticmethod
    def convert_to_wav(
        input_file: str,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Optional[Path]:
        """
        Convert audio file to WAV 16kHz mono format.

        Args:
            input_file: Path to input audio file
            output_dir: Directory for output file. Uses input dir if None.
            progress_callback: Optional callback receiving progress (0.0 to 1.0)

        Returns:
            Path to converted WAV file, or None on error
        """
        processor = AudioProcessor()
        return processor.convert_to_wav(input_file, output_dir, progress_callback)

    @staticmethod
    def is_wav_compatible(file_path: str) -> bool:
        """Check if file is already in WAV 16kHz mono format."""
        processor = AudioProcessor()
        return processor.is_wav_compatible(file_path)


def test_gpu() -> GPUInfo:
    """
    Test GPU capabilities and recommend optimal settings.

    Returns:
        GPUInfo object with test results and recommendations
    """
    engine = TranscriptionEngine(model_size='tiny')
    return engine.get_gpu_info()


# Convenience function for simple usage
def transcribe_file(
    audio_path: str,
    model_size: str = 'large-v3',
    language: Optional[str] = None,
    output_dir: Optional[str] = None
) -> TranscriptionResult:
    """
    Simple convenience function to transcribe a file.

    Args:
        audio_path: Path to audio file
        model_size: Whisper model size
        language: Language code or None for auto-detection
        output_dir: Output directory for SRT file

    Returns:
        TranscriptionResult

    Example:
        result = transcribe_file('audio.wav', model_size='large-v3', language='it')
        if result.success:
            print(f"Done! Saved to: {result.output_path}")
    """
    with TranscriptionEngine(model_size=model_size) as engine:
        return engine.transcribe(
            audio_path=audio_path,
            language=language,
            output_dir=output_dir
        )
