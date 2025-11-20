#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Transcription Service
High-level integration service combining TranscriptionEngine with data layer
"""

import logging
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple
from datetime import datetime
from contextlib import contextmanager

from .transcription import TranscriptionEngine, TranscriptionResult, AudioConverter
from .audio_processor import AudioProcessor
from ..data.database import DatabaseManager, DatabaseError
from ..data.file_manager import FileManager, FileManagerError
from ..data.transcript_manager import TranscriptManager, TranscriptError

logger = logging.getLogger(__name__)


class TranscriptionServiceError(Exception):
    """Base exception for transcription service errors"""
    pass


class TranscriptionService:
    """
    High-level transcription service integrating all components.

    Features:
    - Complete transcription workflow from upload to storage
    - Job creation and status tracking
    - Automatic file deduplication
    - Automatic versioning
    - Progress callbacks with database updates
    - Error handling with rollback
    - Batch processing support
    - Resource management

    Usage:
        service = TranscriptionService(db_path='database/transcription.db')
        result = service.transcribe_file(
            file_path='audio.mp3',
            model_size='large-v3',
            language='it'
        )
    """

    def __init__(
        self,
        db_path: str = 'database/transcription.db',
        model_size: str = 'large-v3',
        device: Optional[str] = None,
        compute_type: Optional[str] = None
    ):
        """
        Initialize transcription service.

        Args:
            db_path: Path to SQLite database
            model_size: Default Whisper model size
            device: Device to use ('cuda' or 'cpu'), auto-detected if None
            compute_type: Compute type, auto-detected if None
        """
        self.db_path = db_path
        self.default_model_size = model_size

        # Initialize database manager
        self.db = DatabaseManager(db_path)

        # Initialize file and transcript managers
        self.file_manager = FileManager(self.db)
        self.transcript_manager = TranscriptManager(self.db)

        # Initialize audio processor
        self.audio_processor = AudioProcessor()

        # Initialize transcription engine (lazy loading)
        self._engine = None
        self._device = device
        self._compute_type = compute_type

        logger.info(
            f"TranscriptionService initialized: db={db_path}, "
            f"model={model_size}"
        )

    @property
    def engine(self) -> TranscriptionEngine:
        """Lazy-loaded transcription engine."""
        if self._engine is None:
            self._engine = TranscriptionEngine(
                model_size=self.default_model_size,
                device=self._device,
                compute_type=self._compute_type
            )
            self._engine.load_model()
        return self._engine

    def transcribe_file(
        self,
        file_path: str,
        model_size: Optional[str] = None,
        task: str = 'transcribe',
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        word_timestamps: bool = False,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        skip_duplicate_check: bool = False
    ) -> Dict[str, Any]:
        """
        Transcribe an audio file with full workflow integration.

        This is the main API method that handles:
        1. File upload with deduplication
        2. Audio format conversion (if needed)
        3. Job creation and tracking
        4. Transcription execution
        5. Result storage with versioning
        6. Database updates

        Args:
            file_path: Path to audio file
            model_size: Whisper model size (uses default if None)
            task: 'transcribe' or 'translate'
            language: Language code or None for auto-detection
            beam_size: Beam search size
            vad_filter: Enable VAD filtering
            word_timestamps: Enable word-level timestamps
            output_dir: Directory for output files (default: same as input)
            progress_callback: Optional callback for progress updates
            skip_duplicate_check: Skip file deduplication check

        Returns:
            Dictionary with complete transcription results and metadata

        Raises:
            TranscriptionServiceError: If transcription workflow fails
        """
        file_path = Path(file_path)
        start_time = time.time()
        job_id = None

        try:
            # 1. Validate and prepare file
            logger.info(f"Starting transcription workflow for: {file_path.name}")

            if not file_path.exists():
                raise TranscriptionServiceError(f"File not found: {file_path}")

            # Get audio metadata
            duration = self.audio_processor.get_duration(str(file_path))
            file_metadata = self.audio_processor.get_metadata(str(file_path))

            logger.info(
                f"Audio metadata: duration={duration:.2f}s, "
                f"format={file_metadata.format}, "
                f"sample_rate={file_metadata.sample_rate}Hz"
            )

            # 2. Convert audio to WAV if needed
            wav_file = file_path
            conversion_needed = not self.audio_processor.is_wav_compatible(str(file_path))

            if conversion_needed:
                logger.info(f"Converting {file_path.suffix} to WAV format...")

                def conversion_progress(progress: float):
                    if progress_callback:
                        progress_callback({
                            'stage': 'conversion',
                            'progress_pct': progress * 100,
                            'message': f'Converting audio... {progress*100:.1f}%'
                        })

                wav_file = self.audio_processor.convert_to_wav(
                    str(file_path),
                    progress_callback=conversion_progress
                )

                if not wav_file:
                    raise TranscriptionServiceError("Audio conversion failed")

                logger.info(f"Conversion complete: {wav_file}")

            # 3. Upload file with deduplication
            logger.info("Uploading file to storage...")

            try:
                file_id, is_new = self.file_manager.upload_file(
                    str(wav_file),
                    original_name=file_path.name,
                    skip_duplicate_check=skip_duplicate_check
                )

                if not is_new:
                    logger.info(f"Duplicate file detected (file_id={file_id})")
                else:
                    logger.info(f"New file uploaded (file_id={file_id})")

            except FileManagerError as e:
                raise TranscriptionServiceError(f"File upload failed: {e}")

            # 4. Create transcription job
            model = model_size or self.default_model_size

            job_id = self.db.create_job(
                file_path=str(file_path),
                model_size=model,
                task_type=task,
                language=language,
                compute_type=self._compute_type or 'auto',
                device=self._device or 'auto',
                beam_size=beam_size,
                duration_seconds=duration
            )

            logger.info(f"Job created: {job_id}")

            # 5. Update job status to processing
            self.db.update_job(
                job_id=job_id,
                status='processing',
                started_at=datetime.now()
            )

            # 6. Create progress wrapper that updates database
            def integrated_progress_callback(progress_data: Dict[str, Any]):
                """Wrapper that updates database and calls user callback."""
                # Update job with current progress (optional metadata)
                # Note: We don't have a progress field in the schema,
                # but we could add it or use metadata

                # Call user callback
                if progress_callback:
                    progress_data['stage'] = 'transcription'
                    progress_callback(progress_data)

            # 7. Perform transcription
            logger.info("Starting transcription...")

            if progress_callback:
                progress_callback({
                    'stage': 'transcription',
                    'progress_pct': 0,
                    'message': 'Transcribing audio...'
                })

            transcription_result = self.engine.transcribe(
                audio_path=str(wav_file),
                output_dir=output_dir,
                task=task,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps,
                progress_callback=integrated_progress_callback
            )

            # 8. Check transcription success
            if not transcription_result.success:
                self.db.update_job(
                    job_id=job_id,
                    status='failed',
                    completed_at=datetime.now(),
                    error_message=transcription_result.error
                )
                raise TranscriptionServiceError(
                    f"Transcription failed: {transcription_result.error}"
                )

            logger.info(
                f"Transcription complete: {transcription_result.segments_count} segments, "
                f"language={transcription_result.language}, "
                f"duration={transcription_result.duration:.2f}s"
            )

            # 9. Parse SRT file to get segments
            segments = self._parse_srt_file(transcription_result.output_path)
            full_text = " ".join([seg['text'] for seg in segments])

            # 10. Save transcription to database
            transcript_id = self.transcript_manager.save_transcript(
                job_id=job_id,
                text=full_text,
                segments=segments,
                language=transcription_result.language or 'unknown',
                srt_path=str(transcription_result.output_path)
            )

            logger.info(f"Transcript saved to database: ID={transcript_id}")

            # 11. Update job status to completed
            processing_time = time.time() - start_time

            self.db.update_job(
                job_id=job_id,
                status='completed',
                detected_language=transcription_result.language,
                language_probability=transcription_result.language_probability,
                completed_at=datetime.now(),
                processing_time_seconds=processing_time
            )

            logger.info(
                f"Job completed successfully: {job_id} "
                f"(processing_time={processing_time:.2f}s)"
            )

            # 12. Cleanup temporary WAV file if conversion was needed
            if conversion_needed and wav_file and wav_file != file_path:
                try:
                    wav_file.unlink()
                    logger.debug(f"Temporary WAV file removed: {wav_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temp file: {e}")

            # 13. Return complete result
            return {
                'success': True,
                'job_id': job_id,
                'file_id': file_id,
                'transcript_id': transcript_id,
                'output_path': str(transcription_result.output_path),
                'segments_count': transcription_result.segments_count,
                'language': transcription_result.language,
                'language_probability': transcription_result.language_probability,
                'duration_seconds': duration,
                'processing_time_seconds': processing_time,
                'was_duplicate': not is_new,
                'model_size': model,
                'device': self.engine.device,
                'compute_type': self.engine.compute_type
            }

        except TranscriptionServiceError:
            raise

        except Exception as e:
            logger.error(f"Transcription workflow failed: {e}", exc_info=True)

            # Update job as failed if job was created
            if job_id:
                try:
                    self.db.update_job(
                        job_id=job_id,
                        status='failed',
                        completed_at=datetime.now(),
                        error_message=str(e)
                    )
                except Exception as db_error:
                    logger.error(f"Failed to update job status: {db_error}")

            raise TranscriptionServiceError(f"Transcription workflow failed: {e}")

    def transcribe_batch(
        self,
        file_paths: List[str],
        batch_progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
        **transcription_options
    ) -> List[Dict[str, Any]]:
        """
        Transcribe multiple files in batch.

        Args:
            file_paths: List of file paths to transcribe
            batch_progress_callback: Optional callback(file_index, total_files, result)
            **transcription_options: Options passed to transcribe_file()

        Returns:
            List of transcription results (one per file)
        """
        results = []
        total_files = len(file_paths)

        logger.info(f"Starting batch transcription: {total_files} files")

        for idx, file_path in enumerate(file_paths, 1):
            logger.info(f"Processing file {idx}/{total_files}: {file_path}")

            try:
                result = self.transcribe_file(file_path, **transcription_options)
                results.append(result)

                if batch_progress_callback:
                    batch_progress_callback(idx, total_files, result)

            except Exception as e:
                logger.error(f"Failed to transcribe {file_path}: {e}")
                results.append({
                    'success': False,
                    'file_path': file_path,
                    'error': str(e)
                })

        successful = sum(1 for r in results if r.get('success', False))
        logger.info(
            f"Batch transcription complete: {successful}/{total_files} successful"
        )

        return results

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a transcription job.

        Args:
            job_id: Job UUID

        Returns:
            Job details dictionary or None if not found
        """
        return self.db.get_job(job_id)

    def get_transcript(
        self,
        transcript_id: int,
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get transcript with segments.

        Args:
            transcript_id: Transcript database ID
            version: Version number (None for current)

        Returns:
            Transcript dictionary with segments
        """
        return self.transcript_manager.get_transcript(transcript_id, version)

    def export_transcript(
        self,
        transcript_id: int,
        format_name: str,
        output_path: str,
        version: Optional[int] = None
    ) -> str:
        """
        Export transcript to specified format.

        Args:
            transcript_id: Transcript database ID
            format_name: Output format (srt, vtt, json, txt, csv)
            output_path: Path to save file
            version: Version number (None for current)

        Returns:
            Formatted content string
        """
        return self.transcript_manager.export_transcript(
            transcript_id=transcript_id,
            format_name=format_name,
            output_path=output_path,
            version=version
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics.

        Returns:
            Dictionary with job, file, and transcript statistics
        """
        db_stats = self.db.get_statistics()
        file_stats = self.file_manager.get_storage_stats()
        transcript_stats = self.transcript_manager.get_statistics()

        return {
            'database': db_stats,
            'storage': file_stats,
            'transcripts': transcript_stats
        }

    def cleanup_resources(self):
        """Clean up resources and free memory."""
        if self._engine:
            self._engine.cleanup()
            self._engine = None
            logger.info("Transcription engine resources cleaned up")

    def close(self):
        """Close service and release all resources."""
        self.cleanup_resources()
        self.file_manager.close()
        self.db.close()
        logger.info("TranscriptionService closed")

    @staticmethod
    def _parse_srt_file(srt_path: Path) -> List[Dict[str, Any]]:
        """
        Parse SRT file into segments.

        Args:
            srt_path: Path to SRT file

        Returns:
            List of segment dictionaries
        """
        segments = []

        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse SRT format
            blocks = content.strip().split('\n\n')

            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) < 3:
                    continue

                # Parse timestamp line
                timestamp_line = lines[1]
                start_str, end_str = timestamp_line.split(' --> ')

                start = TranscriptionService._parse_srt_timestamp(start_str)
                end = TranscriptionService._parse_srt_timestamp(end_str)

                # Get text (may span multiple lines)
                text = '\n'.join(lines[2:])

                segments.append({
                    'start': start,
                    'end': end,
                    'text': text
                })

            return segments

        except Exception as e:
            logger.error(f"Failed to parse SRT file: {e}")
            return []

    @staticmethod
    def _parse_srt_timestamp(timestamp_str: str) -> float:
        """
        Parse SRT timestamp to seconds.

        Args:
            timestamp_str: Timestamp string (HH:MM:SS,mmm)

        Returns:
            Time in seconds
        """
        # Format: HH:MM:SS,mmm
        time_part, millis = timestamp_str.replace(',', '.').rsplit('.', 1)
        hours, minutes, seconds = map(int, time_part.split(':'))

        total_seconds = hours * 3600 + minutes * 60 + seconds
        total_seconds += int(millis) / 1000.0

        return total_seconds

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TranscriptionService(db={self.db_path}, "
            f"model={self.default_model_size})"
        )


# Convenience function for simple usage
def transcribe_file(
    file_path: str,
    model_size: str = 'large-v3',
    language: Optional[str] = None,
    output_dir: Optional[str] = None,
    db_path: str = 'database/transcription.db'
) -> Dict[str, Any]:
    """
    Simple convenience function to transcribe a file.

    Args:
        file_path: Path to audio file
        model_size: Whisper model size
        language: Language code or None for auto-detection
        output_dir: Output directory for files
        db_path: Database path

    Returns:
        Transcription result dictionary

    Example:
        result = transcribe_file('audio.mp3', model_size='large-v3', language='it')
        print(f"Job ID: {result['job_id']}")
        print(f"Transcript saved to: {result['output_path']}")
    """
    with TranscriptionService(db_path=db_path, model_size=model_size) as service:
        return service.transcribe_file(
            file_path=file_path,
            language=language,
            output_dir=output_dir
        )


__all__ = [
    'TranscriptionService',
    'TranscriptionServiceError',
    'transcribe_file'
]
