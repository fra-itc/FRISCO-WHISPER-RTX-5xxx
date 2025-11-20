#!/usr/bin/env python3
"""
Basic usage examples for the TranscriptionEngine

This file demonstrates various ways to use the modular transcription engine.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import (
    TranscriptionEngine,
    AudioConverter,
    transcribe_file,
    test_gpu
)


def example_1_simple_usage():
    """Example 1: Simplest way to transcribe a file"""
    print("=" * 70)
    print("Example 1: Simple Usage")
    print("=" * 70)

    # One-liner transcription
    result = transcribe_file(
        audio_path='audio/myfile.wav',
        model_size='large-v3',
        language='it'  # or None for auto-detection
    )

    if result.success:
        print(f"Success! Transcribed {result.segments_count} segments")
        print(f"Language detected: {result.language} ({result.language_probability:.2%})")
        print(f"Output saved to: {result.output_path}")
    else:
        print(f"Error: {result.error}")


def example_2_context_manager():
    """Example 2: Using context manager for automatic cleanup"""
    print("\n" + "=" * 70)
    print("Example 2: Context Manager Usage")
    print("=" * 70)

    # Context manager automatically loads and cleans up the model
    with TranscriptionEngine(model_size='large-v3') as engine:
        print(f"Engine initialized: {engine}")

        # Transcribe multiple files efficiently
        audio_files = ['audio/file1.wav', 'audio/file2.wav']

        for audio_file in audio_files:
            result = engine.transcribe(
                audio_path=audio_file,
                language=None,  # Auto-detect
                output_dir='transcripts'
            )

            if result.success:
                print(f"✓ {audio_file}: {result.segments_count} segments")
            else:
                print(f"✗ {audio_file}: {result.error}")

    print("Model automatically cleaned up!")


def example_3_with_progress_callback():
    """Example 3: Real-time progress tracking"""
    print("\n" + "=" * 70)
    print("Example 3: Progress Tracking")
    print("=" * 70)

    def progress_handler(data):
        """Custom progress callback"""
        segment_num = data['segment_number']
        text = data['text']
        progress = data['progress_pct']

        print(f"[Segment {segment_num}] {progress:.1f}% - {text[:50]}...")

    engine = TranscriptionEngine(model_size='medium')

    result = engine.transcribe(
        audio_path='audio/myfile.wav',
        language='it',
        progress_callback=progress_handler  # Real-time updates
    )

    engine.cleanup()

    print(f"\nTranscription completed in {result.duration:.1f}s")


def example_4_audio_conversion():
    """Example 4: Convert audio before transcription"""
    print("\n" + "=" * 70)
    print("Example 4: Audio Conversion")
    print("=" * 70)

    converter = AudioConverter()

    # Convert M4A/MP3/etc to WAV
    wav_path = converter.convert_to_wav(
        input_file='audio/podcast.m4a',
        output_dir='audio/converted',
        progress_callback=lambda p: print(f"Converting: {p*100:.1f}%")
    )

    if wav_path:
        print(f"Converted to: {wav_path}")

        # Now transcribe
        result = transcribe_file(wav_path, model_size='large-v3')
        print(f"Transcription: {result.output_path}")

        # Clean up WAV file if desired
        wav_path.unlink()
    else:
        print("Conversion failed")


def example_5_gpu_info():
    """Example 5: Check GPU capabilities"""
    print("\n" + "=" * 70)
    print("Example 5: GPU Information")
    print("=" * 70)

    gpu_info = test_gpu()

    if gpu_info.available:
        print(f"GPU Available: Yes")
        print(f"Device: {gpu_info.device_name}")
        print(f"VRAM: {gpu_info.vram_gb:.1f} GB")
        print(f"CUDA Version: {gpu_info.cuda_version}")
        print(f"Supported compute types: {', '.join(gpu_info.supported_compute_types)}")
        print(f"Recommended: {gpu_info.recommended_compute_type}")
    else:
        print("GPU not available - will use CPU (slower)")


def example_6_custom_configuration():
    """Example 6: Custom engine configuration"""
    print("\n" + "=" * 70)
    print("Example 6: Custom Configuration")
    print("=" * 70)

    # Create engine with specific settings
    engine = TranscriptionEngine(
        model_size='medium',
        device='cuda',
        compute_type='float16',
        auto_detect_gpu=False  # Manual configuration
    )

    # Transcribe with custom parameters
    result = engine.transcribe(
        audio_path='audio/myfile.wav',
        task='translate',  # Translate to English
        language='it',  # Source language
        beam_size=10,  # Higher accuracy (slower)
        vad_filter=True,  # Voice activity detection
        word_timestamps=True  # Word-level timing
    )

    print(f"Translation result: {result.output_path}")
    engine.cleanup()


def example_7_retry_on_failure():
    """Example 7: Automatic retry on failure"""
    print("\n" + "=" * 70)
    print("Example 7: Retry Logic")
    print("=" * 70)

    engine = TranscriptionEngine(model_size='large-v3')

    # Automatically retry up to 3 times on failure
    result = engine.transcribe_with_retry(
        audio_path='audio/difficult_file.wav',
        max_retries=3,
        language='it'
    )

    if result.success:
        print(f"Success after retries: {result.output_path}")
    else:
        print(f"Failed after all retries: {result.error}")

    engine.cleanup()


def example_8_batch_processing():
    """Example 8: Efficient batch processing"""
    print("\n" + "=" * 70)
    print("Example 8: Batch Processing")
    print("=" * 70)

    from pathlib import Path

    audio_dir = Path('audio')
    audio_files = list(audio_dir.glob('*.wav')) + list(audio_dir.glob('*.m4a'))

    print(f"Found {len(audio_files)} files to process")

    # Process all files with a single model instance
    with TranscriptionEngine(model_size='large-v3') as engine:
        results = []

        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n[{i}/{len(audio_files)}] Processing: {audio_file.name}")

            result = engine.transcribe(
                audio_path=str(audio_file),
                language=None,  # Auto-detect
                output_dir='transcripts'
            )

            results.append((audio_file.name, result))

            if result.success:
                print(f"✓ Success: {result.segments_count} segments")
            else:
                print(f"✗ Failed: {result.error}")

    # Summary
    success_count = sum(1 for _, r in results if r.success)
    print(f"\n{'=' * 70}")
    print(f"Batch complete: {success_count}/{len(results)} successful")


if __name__ == '__main__':
    print("TranscriptionEngine - Usage Examples")
    print("=" * 70)

    # Run all examples (comment out ones you don't want to run)

    # example_1_simple_usage()
    # example_2_context_manager()
    # example_3_with_progress_callback()
    # example_4_audio_conversion()
    example_5_gpu_info()
    # example_6_custom_configuration()
    # example_7_retry_on_failure()
    # example_8_batch_processing()

    print("\n" + "=" * 70)
    print("Examples completed!")
