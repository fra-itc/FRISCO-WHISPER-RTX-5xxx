#!/usr/bin/env python3
"""
Example script demonstrating the new GPU Manager and Audio Processor modules.

This script shows how to use the modular components for GPU management
and audio processing independently or integrated with TranscriptionEngine.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import (
    GPUManager,
    AudioProcessor,
    TranscriptionEngine,
    get_default_device,
    print_gpu_info,
    convert_audio_file
)


def example_gpu_manager():
    """Demonstrate GPU Manager usage."""
    print("\n" + "=" * 80)
    print("GPU MANAGER EXAMPLES")
    print("=" * 80)

    # Initialize GPU Manager
    gpu_manager = GPUManager()

    # Print comprehensive GPU summary
    print("\n1. GPU Summary:")
    gpu_manager.print_gpu_summary()

    # Check if CUDA is available
    if gpu_manager.has_cuda:
        print(f"\nCUDA available with {len(gpu_manager.available_gpus)} GPU(s)")

        # Get info for first GPU
        gpu_info = gpu_manager.get_gpu_info(0)
        if gpu_info:
            print(f"\nFirst GPU Details:")
            print(f"  Name: {gpu_info.name}")
            print(f"  Total Memory: {gpu_info.total_memory_gb:.2f} GB")
            print(f"  Available Memory: {gpu_info.available_memory_gb:.2f} GB")
            print(f"  CUDA Capability: {gpu_info.cuda_capability}")
            print(f"  Supported Compute Types: {', '.join(gpu_info.supported_compute_types)}")
            print(f"  Recommended: {gpu_info.recommended_compute_type}")

        # Get memory info
        mem_info = gpu_manager.get_memory_info(0)
        if mem_info:
            print(f"\nMemory Status:")
            print(f"  Free: {mem_info.free_gb:.2f} GB")
            print(f"  Allocated: {mem_info.allocated_gb:.2f} GB")
            print(f"  Utilization: {mem_info.utilization_percent:.1f}%")

        # Select best GPU
        best_gpu = gpu_manager.select_best_gpu()
        print(f"\nBest GPU for transcription: {best_gpu}")

        # Get fallback configurations
        print(f"\nFallback configurations:")
        for i, config in enumerate(gpu_manager.get_fallback_configs()[:3], 1):
            print(f"  {i}. Device: {config['device']}, Compute: {config['compute']}")

    else:
        print("\nCUDA not available - CPU mode only")

    # Quick convenience functions
    print(f"\nDefault device: {get_default_device()}")


def example_audio_processor():
    """Demonstrate Audio Processor usage."""
    print("\n" + "=" * 80)
    print("AUDIO PROCESSOR EXAMPLES")
    print("=" * 80)

    # Initialize Audio Processor
    processor = AudioProcessor()

    # Show supported formats
    print(f"\nSupported audio formats:")
    formats = processor.get_supported_formats()
    print(f"  {', '.join(formats)}")

    # Check if a sample audio file exists
    audio_dir = Path(__file__).parent.parent / "audio"
    sample_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.m4a")) + list(audio_dir.glob("*.mp3"))

    if sample_files:
        sample_file = sample_files[0]
        print(f"\n2. Analyzing sample file: {sample_file.name}")

        # Detect format and metadata
        metadata = processor.detect_format(str(sample_file))
        if metadata and metadata.is_valid:
            print(f"\nMetadata:")
            print(f"  Format: {metadata.format}")
            print(f"  Codec: {metadata.codec}")
            print(f"  Duration: {metadata.duration:.2f}s" if metadata.duration else "  Duration: Unknown")
            print(f"  Sample Rate: {metadata.sample_rate} Hz" if metadata.sample_rate else "  Sample Rate: Unknown")
            print(f"  Channels: {metadata.channels}" if metadata.channels else "  Channels: Unknown")
            print(f"  Bitrate: {metadata.bit_rate / 1000:.0f} kbps" if metadata.bit_rate else "  Bitrate: Unknown")
            print(f"  File Size: {metadata.file_size_mb:.2f} MB")

        # Validate audio
        is_valid = processor.validate_audio(str(sample_file))
        print(f"\nValidation: {'VALID' if is_valid else 'INVALID'}")

        # Check WAV compatibility
        is_compatible = processor.is_wav_compatible(str(sample_file))
        print(f"WAV 16kHz mono compatible: {'YES' if is_compatible else 'NO'}")

        # Get duration
        duration = processor.get_duration(str(sample_file))
        if duration:
            print(f"Duration: {duration:.2f} seconds ({duration / 60:.2f} minutes)")

    else:
        print("\nNo audio files found in audio/ directory")
        print("Place some audio files there to test audio processing features")


def example_integrated_usage():
    """Demonstrate integrated usage with TranscriptionEngine."""
    print("\n" + "=" * 80)
    print("INTEGRATED USAGE WITH TRANSCRIPTION ENGINE")
    print("=" * 80)

    # Create engine (automatically uses GPU Manager and Audio Processor)
    engine = TranscriptionEngine(model_size='tiny')  # Use tiny model for demo

    print(f"\nTranscription Engine Configuration:")
    print(f"  Model: {engine.model_size}")
    print(f"  Device: {engine.device}")
    print(f"  Compute Type: {engine.compute_type}")

    if engine.gpu_info and engine.gpu_info.available:
        print(f"  GPU: {engine.gpu_info.device_name}")
        print(f"  VRAM: {engine.gpu_info.vram_gb:.2f} GB")

    # Access the GPU manager directly
    print(f"\nGPU Manager integrated: {engine.gpu_manager is not None}")
    print(f"Audio Processor integrated: {engine.audio_processor is not None}")

    # Example: Get memory info through engine
    if engine.device == 'cuda' and engine.device_index is not None:
        mem_info = engine.gpu_manager.get_memory_info(engine.device_index)
        if mem_info:
            print(f"\nCurrent VRAM usage:")
            print(f"  Free: {mem_info.free_gb:.2f} GB")
            print(f"  Utilization: {mem_info.utilization_percent:.1f}%")


def example_multi_gpu():
    """Demonstrate multi-GPU selection."""
    print("\n" + "=" * 80)
    print("MULTI-GPU SUPPORT")
    print("=" * 80)

    gpu_manager = GPUManager()

    if len(gpu_manager.available_gpus) > 1:
        print(f"\nDetected {len(gpu_manager.available_gpus)} GPUs")

        for device_id in gpu_manager.available_gpus:
            info = gpu_manager.get_gpu_info(device_id)
            if info:
                print(f"\nGPU {device_id}:")
                print(f"  Name: {info.name}")
                print(f"  Memory: {info.total_memory_gb:.2f} GB")
                print(f"  Recommended Compute: {info.recommended_compute_type}")

        # Create engine with specific GPU
        print(f"\nCreating engine on GPU 1...")
        engine = TranscriptionEngine(model_size='tiny', device_index=1)
        print(f"Engine using GPU: {engine.device_index}")

    elif len(gpu_manager.available_gpus) == 1:
        print(f"\nSingle GPU system - automatic selection")
    else:
        print(f"\nNo GPUs available - CPU mode")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("GPU MANAGER & AUDIO PROCESSOR MODULE EXAMPLES")
    print("=" * 80)

    try:
        # GPU Manager examples
        example_gpu_manager()

        # Audio Processor examples
        example_audio_processor()

        # Integrated usage
        example_integrated_usage()

        # Multi-GPU support
        example_multi_gpu()

        print("\n" + "=" * 80)
        print("EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
