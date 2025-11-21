#!/usr/bin/env python3
"""
Audio Processor Module - Comprehensive Audio Format Detection and Processing

This module provides complete audio handling capabilities including format detection,
validation, conversion, metadata extraction, and audio manipulation.

Features:
- Format detection via ffprobe
- Audio validation (sample rate, channels, codec)
- Multi-format conversion to WAV 16kHz mono
- Duration calculation and metadata extraction
- Audio splitting/chunking for large files
- Progress callbacks for long operations
- Support for multiple audio formats

Supported formats:
- WAV, MP3, M4A, AAC, FLAC, OGG, OPUS
- MP4 (audio track)
- WAPTT (WhatsApp audio)

Example:
    processor = AudioProcessor()

    # Detect format and metadata
    metadata = processor.detect_format('audio.m4a')
    print(f"Format: {metadata.format}, Duration: {metadata.duration}s")

    # Convert to WAV
    wav_path = processor.convert_to_wav('audio.m4a', 'output/')

    # Validate audio
    is_valid = processor.validate_audio('audio.wav')
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """Comprehensive audio file metadata."""
    file_path: Path
    format: str
    codec: Optional[str] = None
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bit_rate: Optional[int] = None
    file_size_mb: float = 0.0
    is_valid: bool = True
    error_message: Optional[str] = None
    extra_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionResult:
    """Result of audio conversion operation."""
    success: bool
    output_path: Optional[Path] = None
    original_format: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None


class AudioProcessor:
    """
    Comprehensive audio processing and format handling.

    Handles audio format detection, validation, conversion,
    and metadata extraction for transcription workflows.

    Attributes:
        supported_formats: List of supported audio format extensions
        target_sample_rate: Target sample rate for conversion (16000 Hz)
        target_channels: Target channel count for conversion (1 = mono)
    """

    # Supported input formats
    SUPPORTED_FORMATS = [
        '.wav', '.mp3', '.m4a', '.aac', '.flac',
        '.ogg', '.opus', '.mp4', '.wma', '.waptt'
    ]

    # Target audio specifications for transcription
    TARGET_SAMPLE_RATE = 16000
    TARGET_CHANNELS = 1
    TARGET_CODEC = 'pcm_s16le'

    def __init__(self):
        """Initialize Audio Processor."""
        self.supported_formats = self.SUPPORTED_FORMATS.copy()
        self.target_sample_rate = self.TARGET_SAMPLE_RATE
        self.target_channels = self.TARGET_CHANNELS

        # Check for local ffmpeg first, then system
        self.ffmpeg_path, self.ffprobe_path = self._find_ffmpeg_binaries()
        self._ffmpeg_available = self._check_ffmpeg()

    def _find_ffmpeg_binaries(self) -> tuple:
        """
        Find ffmpeg and ffprobe binaries.

        Search order:
        1. Project's bin/ directory (local installation)
        2. System PATH

        Returns:
            Tuple of (ffmpeg_path, ffprobe_path)
        """
        import platform

        # Determine binary names
        is_windows = platform.system().lower() == 'windows'
        ffmpeg_name = 'ffmpeg.exe' if is_windows else 'ffmpeg'
        ffprobe_name = 'ffprobe.exe' if is_windows else 'ffprobe'

        # 1. Check project's bin/ directory
        project_root = Path(__file__).parent.parent.parent
        local_bin_dir = project_root / 'bin'

        local_ffmpeg = local_bin_dir / ffmpeg_name
        local_ffprobe = local_bin_dir / ffprobe_name

        if local_ffmpeg.exists() and local_ffprobe.exists():
            logger.info(f"Using local ffmpeg from {local_bin_dir}")
            return str(local_ffmpeg), str(local_ffprobe)

        # 2. Use system PATH (default behavior)
        logger.info("Using system ffmpeg from PATH")
        return ffmpeg_name, ffprobe_name

    def _check_ffmpeg(self) -> bool:
        """
        Check if ffmpeg and ffprobe are available.

        Returns:
            True if both tools are available
        """
        try:
            subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                check=True
            )
            subprocess.run(
                [self.ffprobe_path, '-version'],
                capture_output=True,
                check=True
            )
            logger.info(f"ffmpeg available: {self.ffmpeg_path}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error(
                f"ffmpeg/ffprobe not found - audio processing disabled\n"
                f"  Searched: {self.ffmpeg_path}, {self.ffprobe_path}\n"
                f"  Solution: Run 'python setup_ffmpeg.py' to install locally"
            )
            return False

    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if audio format is supported.

        Args:
            file_path: Path to audio file

        Returns:
            True if format is supported
        """
        path = Path(file_path)
        return path.suffix.lower() in self.supported_formats

    def detect_format(self, file_path: str) -> Optional[AudioMetadata]:
        """
        Detect audio format and extract comprehensive metadata.

        Args:
            file_path: Path to audio file

        Returns:
            AudioMetadata object with file information, or None on error
        """
        path = Path(file_path)

        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return AudioMetadata(
                file_path=path,
                format='unknown',
                is_valid=False,
                error_message="File not found"
            )

        if not self._ffmpeg_available:
            return AudioMetadata(
                file_path=path,
                format=path.suffix.lower().lstrip('.'),
                file_size_mb=path.stat().st_size / (1024**2),
                is_valid=False,
                error_message="ffmpeg not available"
            )

        try:
            # Run ffprobe to get metadata
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            data = json.loads(result.stdout)

            # Extract format information
            format_info = data.get('format', {})

            # Find audio stream
            audio_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break

            if not audio_stream:
                return AudioMetadata(
                    file_path=path,
                    format=format_info.get('format_name', 'unknown'),
                    is_valid=False,
                    error_message="No audio stream found"
                )

            # Extract metadata
            metadata = AudioMetadata(
                file_path=path,
                format=format_info.get('format_name', 'unknown'),
                codec=audio_stream.get('codec_name'),
                duration=float(format_info.get('duration', 0)),
                sample_rate=int(audio_stream.get('sample_rate', 0)),
                channels=int(audio_stream.get('channels', 0)),
                bit_rate=int(format_info.get('bit_rate', 0)),
                file_size_mb=path.stat().st_size / (1024**2),
                is_valid=True,
                extra_info={
                    'codec_long_name': audio_stream.get('codec_long_name'),
                    'channel_layout': audio_stream.get('channel_layout'),
                    'bit_depth': audio_stream.get('bits_per_sample')
                }
            )

            return metadata

        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e.stderr}")
            return AudioMetadata(
                file_path=path,
                format='unknown',
                is_valid=False,
                error_message=f"ffprobe error: {e.stderr}"
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe output: {e}")
            return AudioMetadata(
                file_path=path,
                format='unknown',
                is_valid=False,
                error_message="Failed to parse audio metadata"
            )
        except Exception as e:
            logger.error(f"Error detecting format: {e}")
            return AudioMetadata(
                file_path=path,
                format='unknown',
                is_valid=False,
                error_message=str(e)
            )

    def validate_audio(self, file_path: str) -> bool:
        """
        Validate that audio file is readable and contains audio data.

        Args:
            file_path: Path to audio file

        Returns:
            True if audio is valid
        """
        metadata = self.detect_format(file_path)

        if not metadata or not metadata.is_valid:
            return False

        # Check essential properties
        if not metadata.duration or metadata.duration <= 0:
            logger.warning(f"Invalid duration: {metadata.duration}")
            return False

        if not metadata.sample_rate or metadata.sample_rate <= 0:
            logger.warning(f"Invalid sample rate: {metadata.sample_rate}")
            return False

        if not metadata.channels or metadata.channels <= 0:
            logger.warning(f"Invalid channel count: {metadata.channels}")
            return False

        return True

    def get_duration(self, file_path: str) -> Optional[float]:
        """
        Get audio file duration in seconds.

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds, or None on error
        """
        metadata = self.detect_format(file_path)
        return metadata.duration if metadata else None

    def is_wav_compatible(self, file_path: str) -> bool:
        """
        Check if file is already in target WAV format (16kHz mono PCM).

        Args:
            file_path: Path to audio file

        Returns:
            True if already in target format
        """
        metadata = self.detect_format(file_path)

        if not metadata or not metadata.is_valid:
            return False

        is_correct_codec = metadata.codec == 'pcm_s16le'
        is_correct_rate = metadata.sample_rate == self.TARGET_SAMPLE_RATE
        is_correct_channels = metadata.channels == self.TARGET_CHANNELS

        return is_correct_codec and is_correct_rate and is_correct_channels

    def convert_to_wav(
        self,
        input_file: str,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        overwrite: bool = False
    ) -> Optional[Path]:
        """
        Convert audio file to WAV 16kHz mono format.

        Args:
            input_file: Path to input audio file
            output_dir: Directory for output file (uses input dir if None)
            progress_callback: Optional callback receiving progress (0.0 to 1.0)
            overwrite: Whether to overwrite existing output file

        Returns:
            Path to converted WAV file, or None on error
        """
        input_path = Path(input_file)

        if not input_path.exists():
            logger.error(f"Input file not found: {input_file}")
            return None

        if not self._ffmpeg_available:
            logger.error("ffmpeg not available")
            return None

        # Determine output path
        if output_dir is None:
            output_dir = input_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{input_path.stem}.wav"

        # Check if already exists
        if output_path.exists() and not overwrite:
            logger.info(f"Output file already exists: {output_path}")
            return output_path

        # Get duration for progress tracking
        duration = self.get_duration(input_file)

        try:
            # Build ffmpeg command
            cmd = [
                self.ffmpeg_path,
                '-i', str(input_path),
                '-ar', str(self.TARGET_SAMPLE_RATE),
                '-ac', str(self.TARGET_CHANNELS),
                '-c:a', self.TARGET_CODEC,
                '-progress', 'pipe:1',
                '-y' if overwrite else '-n',
                str(output_path)
            ]

            # Run conversion
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )

            # Track progress
            if progress_callback and duration:
                for line in process.stdout:
                    if line.startswith('out_time_us='):
                        try:
                            time_us = int(line.split('=')[1].strip())
                            progress = min(time_us / (duration * 1_000_000), 1.0)
                            progress_callback(progress)
                        except (ValueError, IndexError):
                            pass

            process.wait()

            if process.returncode != 0:
                stderr = process.stderr.read() if process.stderr else ""
                logger.error(f"ffmpeg conversion failed: {stderr}")
                return None

            logger.info(f"Converted audio to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            return None

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from audio file.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with metadata fields
        """
        metadata = self.detect_format(file_path)

        if not metadata:
            return {}

        return {
            'file_path': str(metadata.file_path),
            'format': metadata.format,
            'codec': metadata.codec,
            'duration': metadata.duration,
            'sample_rate': metadata.sample_rate,
            'channels': metadata.channels,
            'bit_rate': metadata.bit_rate,
            'file_size_mb': metadata.file_size_mb,
            'is_valid': metadata.is_valid,
            **metadata.extra_info
        }

    def split_audio(
        self,
        file_path: str,
        chunk_duration: float,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Path]:
        """
        Split audio file into chunks of specified duration.

        Useful for processing very large audio files that may cause
        memory issues or for parallel processing.

        Args:
            file_path: Path to audio file
            chunk_duration: Duration of each chunk in seconds
            output_dir: Directory for output chunks (uses input dir if None)
            progress_callback: Optional callback receiving (current_chunk, total_chunks)

        Returns:
            List of paths to audio chunks
        """
        input_path = Path(file_path)

        if not input_path.exists():
            logger.error(f"Input file not found: {file_path}")
            return []

        if not self._ffmpeg_available:
            logger.error("ffmpeg not available")
            return []

        # Get audio duration
        total_duration = self.get_duration(file_path)
        if not total_duration:
            logger.error("Could not determine audio duration")
            return []

        # Calculate number of chunks
        num_chunks = int(total_duration / chunk_duration) + (1 if total_duration % chunk_duration else 0)

        # Determine output directory
        if output_dir is None:
            output_dir = input_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        chunks = []

        try:
            for i in range(num_chunks):
                start_time = i * chunk_duration
                output_path = output_dir / f"{input_path.stem}_chunk_{i:03d}.wav"

                cmd = [
                    self.ffmpeg_path,
                    '-i', str(input_path),
                    '-ss', str(start_time),
                    '-t', str(chunk_duration),
                    '-ar', str(self.TARGET_SAMPLE_RATE),
                    '-ac', str(self.TARGET_CHANNELS),
                    '-c:a', self.TARGET_CODEC,
                    '-y',
                    str(output_path)
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    chunks.append(output_path)
                    logger.info(f"Created chunk {i + 1}/{num_chunks}: {output_path}")

                    if progress_callback:
                        progress_callback(i + 1, num_chunks)
                else:
                    logger.error(f"Failed to create chunk {i + 1}: {result.stderr}")

            return chunks

        except Exception as e:
            logger.error(f"Error splitting audio: {e}")
            return chunks  # Return whatever chunks were successfully created

    def concatenate_audio(
        self,
        file_paths: List[str],
        output_file: str
    ) -> Optional[Path]:
        """
        Concatenate multiple audio files into one.

        Args:
            file_paths: List of audio file paths to concatenate
            output_file: Path for output file

        Returns:
            Path to concatenated file, or None on error
        """
        if not file_paths:
            logger.error("No input files provided")
            return None

        if not self._ffmpeg_available:
            logger.error("ffmpeg not available")
            return None

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create temporary file list for ffmpeg concat
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for file_path in file_paths:
                    f.write(f"file '{Path(file_path).absolute()}'\n")
                list_file = f.name

            # Run ffmpeg concat
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                '-y',
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            # Clean up temp file
            Path(list_file).unlink()

            if result.returncode == 0:
                logger.info(f"Concatenated {len(file_paths)} files to: {output_path}")
                return output_path
            else:
                logger.error(f"Concatenation failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error concatenating audio: {e}")
            return None

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported audio formats.

        Returns:
            List of supported file extensions
        """
        return self.supported_formats.copy()

    def __repr__(self) -> str:
        """String representation of AudioProcessor."""
        return f"AudioProcessor(ffmpeg_available={self._ffmpeg_available})"


# Convenience functions for quick access

def convert_audio_file(input_file: str, output_dir: Optional[str] = None) -> Optional[Path]:
    """
    Quick conversion function for audio files.

    Args:
        input_file: Path to input audio file
        output_dir: Directory for output file

    Returns:
        Path to converted WAV file
    """
    processor = AudioProcessor()
    return processor.convert_to_wav(input_file, output_dir)


def get_audio_info(file_path: str) -> Dict[str, Any]:
    """
    Quick function to get audio metadata.

    Args:
        file_path: Path to audio file

    Returns:
        Dictionary with audio metadata
    """
    processor = AudioProcessor()
    return processor.extract_metadata(file_path)


def validate_audio_file(file_path: str) -> bool:
    """
    Quick validation function for audio files.

    Args:
        file_path: Path to audio file

    Returns:
        True if audio is valid
    """
    processor = AudioProcessor()
    return processor.validate_audio(file_path)
