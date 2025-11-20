#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Integrated Transcription Examples
Demonstrates the complete transcription workflow using TranscriptionService
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.transcription_service import TranscriptionService, transcribe_file
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_transcription():
    """Example 1: Basic transcription with minimal configuration."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Transcription")
    print("=" * 80)

    # Simple one-line transcription
    result = transcribe_file(
        file_path='audio/example.mp3',
        model_size='medium',
        language='it'
    )

    if result['success']:
        print(f"\nTranscription completed successfully!")
        print(f"Job ID: {result['job_id']}")
        print(f"Transcript ID: {result['transcript_id']}")
        print(f"Output file: {result['output_path']}")
        print(f"Language: {result['language']} ({result['language_probability']:.2%} confidence)")
        print(f"Segments: {result['segments_count']}")
        print(f"Processing time: {result['processing_time_seconds']:.2f} seconds")
    else:
        print(f"Transcription failed: {result.get('error')}")


def example_with_progress_callback():
    """Example 2: Transcription with progress monitoring."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Transcription with Progress Monitoring")
    print("=" * 80)

    def progress_handler(progress_data: dict):
        """Handle progress updates."""
        stage = progress_data.get('stage', 'unknown')

        if stage == 'conversion':
            print(f"[CONVERT] {progress_data['progress_pct']:.1f}% - {progress_data['message']}")

        elif stage == 'transcription':
            segment_num = progress_data.get('segment_number')
            if segment_num:
                text = progress_data['text'][:50]  # First 50 chars
                progress_pct = progress_data['progress_pct']
                print(f"[SEGMENT {segment_num:03d}] {progress_pct:.1f}% - {text}...")
            else:
                print(f"[TRANSCRIBE] {progress_data.get('message', 'Starting...')}")

    # Create service instance
    with TranscriptionService(model_size='large-v3') as service:
        result = service.transcribe_file(
            file_path='audio/example.mp3',
            language='it',
            progress_callback=progress_handler
        )

        if result['success']:
            print(f"\n✓ Transcription completed!")
            print(f"  Job ID: {result['job_id']}")
            print(f"  Processing time: {result['processing_time_seconds']:.2f}s")


def example_batch_processing():
    """Example 3: Batch processing multiple files."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Batch Processing")
    print("=" * 80)

    # List of files to process
    audio_files = [
        'audio/file1.mp3',
        'audio/file2.wav',
        'audio/file3.m4a'
    ]

    def batch_progress(file_index: int, total_files: int, result: dict):
        """Handle batch progress updates."""
        print(f"\n[{file_index}/{total_files}] Completed: {Path(result.get('file_path', '')).name}")
        if result['success']:
            print(f"  ✓ Job ID: {result['job_id']}")
            print(f"  ✓ Segments: {result['segments_count']}")
            print(f"  ✓ Language: {result['language']}")
        else:
            print(f"  ✗ Error: {result.get('error')}")

    # Process batch
    with TranscriptionService(model_size='medium') as service:
        results = service.transcribe_batch(
            file_paths=audio_files,
            batch_progress_callback=batch_progress,
            language='it',
            beam_size=5
        )

        # Summary
        successful = sum(1 for r in results if r.get('success', False))
        print(f"\n{'=' * 80}")
        print(f"Batch Summary: {successful}/{len(results)} files transcribed successfully")


def example_job_status_monitoring():
    """Example 4: Monitor job status."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Job Status Monitoring")
    print("=" * 80)

    with TranscriptionService() as service:
        # Start transcription
        result = service.transcribe_file(
            file_path='audio/example.mp3',
            language='it'
        )

        job_id = result['job_id']

        # Get job status
        job_status = service.get_job_status(job_id)

        print(f"\nJob Details:")
        print(f"  Job ID: {job_status['job_id']}")
        print(f"  File: {job_status['file_name']}")
        print(f"  Status: {job_status['status']}")
        print(f"  Model: {job_status['model_size']}")
        print(f"  Language: {job_status['detected_language']}")
        print(f"  Duration: {job_status['duration_seconds']:.2f}s")
        print(f"  Processing Time: {job_status['processing_time_seconds']:.2f}s")
        print(f"  Created: {job_status['created_at']}")
        print(f"  Completed: {job_status['completed_at']}")


def example_export_formats():
    """Example 5: Export transcript to different formats."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Export to Multiple Formats")
    print("=" * 80)

    with TranscriptionService() as service:
        # Transcribe file
        result = service.transcribe_file(
            file_path='audio/example.mp3',
            language='it'
        )

        if not result['success']:
            print("Transcription failed!")
            return

        transcript_id = result['transcript_id']

        # Export to different formats
        formats = ['srt', 'vtt', 'json', 'txt', 'csv']

        for fmt in formats:
            output_path = f'output/transcript.{fmt}'

            try:
                content = service.export_transcript(
                    transcript_id=transcript_id,
                    format_name=fmt,
                    output_path=output_path
                )

                print(f"✓ Exported to {fmt.upper()}: {output_path}")

                # Show preview for text format
                if fmt == 'txt':
                    preview = content[:200] + '...' if len(content) > 200 else content
                    print(f"  Preview: {preview}")

            except Exception as e:
                print(f"✗ Failed to export to {fmt}: {e}")


def example_transcript_versioning():
    """Example 6: Working with transcript versions."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Transcript Versioning")
    print("=" * 80)

    with TranscriptionService() as service:
        # Transcribe file
        result = service.transcribe_file(
            file_path='audio/example.mp3',
            language='it'
        )

        transcript_id = result['transcript_id']

        # Get current transcript
        transcript = service.get_transcript(transcript_id)

        print(f"\nCurrent Version:")
        print(f"  Version: {transcript['version_number']}")
        print(f"  Segments: {transcript['segment_count']}")
        print(f"  Created by: {transcript['created_by']}")
        print(f"  Note: {transcript['change_note']}")

        # Get version history
        versions = service.transcript_manager.get_versions(transcript_id)

        print(f"\nVersion History: ({len(versions)} versions)")
        for v in versions:
            current_marker = " [CURRENT]" if v['is_current'] else ""
            print(
                f"  v{v['version_number']}: {v['segment_count']} segments, "
                f"by {v['created_by']}, {v['created_at']}{current_marker}"
            )


def example_error_handling():
    """Example 7: Error handling and recovery."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Error Handling")
    print("=" * 80)

    with TranscriptionService() as service:
        # Try to transcribe non-existent file
        try:
            result = service.transcribe_file(
                file_path='audio/nonexistent.mp3',
                language='it'
            )
        except Exception as e:
            print(f"✓ Caught expected error: {e}")

        # Try invalid format
        try:
            result = service.transcribe_file(
                file_path='document.pdf',  # Not an audio file
                language='it'
            )
        except Exception as e:
            print(f"✓ Caught expected error: {e}")

        print("\nError handling working correctly!")


def example_statistics():
    """Example 8: Get system statistics."""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: System Statistics")
    print("=" * 80)

    with TranscriptionService() as service:
        stats = service.get_statistics()

        print("\nDatabase Statistics:")
        db_stats = stats['database']
        print(f"  Total jobs: {db_stats.get('total_jobs', 0)}")
        print(f"  Completed: {db_stats.get('completed_jobs', 0)}")
        print(f"  Failed: {db_stats.get('failed_jobs', 0)}")
        print(f"  Pending: {db_stats.get('pending_jobs', 0)}")

        print("\nStorage Statistics:")
        storage = stats['storage']
        print(f"  Total files: {storage.get('total_files', 0)}")
        print(f"  Total size: {storage.get('total_size_formatted', 'N/A')}")
        print(f"  Quota used: {storage.get('quota_used_percentage', 0):.1f}%")
        print(f"  Available: {storage.get('quota_available_formatted', 'N/A')}")

        print("\nTranscript Statistics:")
        transcript_stats = stats['transcripts']
        print(f"  Total transcripts: {transcript_stats.get('total_transcripts', 0)}")
        print(f"  Total versions: {transcript_stats.get('total_versions', 0)}")
        print(f"  Average versions per transcript: {transcript_stats.get('avg_versions_per_transcript', 0):.1f}")
        print(f"  Total exports: {transcript_stats.get('total_exports', 0)}")


def example_custom_configuration():
    """Example 9: Custom configuration and options."""
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Custom Configuration")
    print("=" * 80)

    # Create service with custom configuration
    service = TranscriptionService(
        db_path='database/custom_transcription.db',
        model_size='small',  # Faster, smaller model
        device='cuda',  # Force GPU
        compute_type='float16'  # Specific compute type
    )

    with service:
        result = service.transcribe_file(
            file_path='audio/example.mp3',
            language='it',
            beam_size=3,  # Faster beam size
            vad_filter=True,  # Enable VAD
            word_timestamps=True,  # Enable word-level timestamps
            output_dir='output/custom'
        )

        if result['success']:
            print(f"\nTranscription with custom config:")
            print(f"  Device: {result['device']}")
            print(f"  Compute type: {result['compute_type']}")
            print(f"  Model: {result['model_size']}")
            print(f"  Processing time: {result['processing_time_seconds']:.2f}s")


def example_deduplication():
    """Example 10: File deduplication."""
    print("\n" + "=" * 80)
    print("EXAMPLE 10: File Deduplication")
    print("=" * 80)

    with TranscriptionService() as service:
        # Transcribe same file twice
        print("\nFirst transcription:")
        result1 = service.transcribe_file(
            file_path='audio/example.mp3',
            language='it'
        )
        print(f"  File ID: {result1['file_id']}")
        print(f"  Was duplicate: {result1['was_duplicate']}")

        print("\nSecond transcription (same file):")
        result2 = service.transcribe_file(
            file_path='audio/example.mp3',
            language='it'
        )
        print(f"  File ID: {result2['file_id']}")
        print(f"  Was duplicate: {result2['was_duplicate']}")

        if result1['file_id'] == result2['file_id']:
            print("\n✓ Deduplication working! Same file ID used for both transcriptions.")
        else:
            print("\n✗ Different file IDs - deduplication may not be working.")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("FRISCO WHISPER RTX 5xxx - Integrated Transcription Examples")
    print("=" * 80)

    examples = [
        ("Basic Transcription", example_basic_transcription),
        ("Progress Monitoring", example_with_progress_callback),
        ("Batch Processing", example_batch_processing),
        ("Job Status Monitoring", example_job_status_monitoring),
        ("Export Formats", example_export_formats),
        ("Transcript Versioning", example_transcript_versioning),
        ("Error Handling", example_error_handling),
        ("System Statistics", example_statistics),
        ("Custom Configuration", example_custom_configuration),
        ("File Deduplication", example_deduplication),
    ]

    print("\nAvailable examples:")
    for idx, (name, _) in enumerate(examples, 1):
        print(f"  {idx}. {name}")

    print("\nTo run a specific example, modify the script.")
    print("For now, running Example 1 (Basic Transcription)...\n")

    # Run example 1 by default
    try:
        example_basic_transcription()
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)

    print("\n" + "=" * 80)
    print("Example completed!")
    print("=" * 80)


if __name__ == '__main__':
    main()
