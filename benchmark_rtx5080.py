"""
RTX 5080 Transcription Benchmark
Tests real-world performance with faster-whisper
"""

import torch
import time
import os
from faster_whisper import WhisperModel
import subprocess
import json

def get_audio_duration(audio_path):
    """Get audio duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except:
        return None

def benchmark_transcription(audio_file, model_size='tiny', compute_type='float16'):
    """Run transcription benchmark"""

    print("=" * 70)
    print("RTX 5080 TRANSCRIPTION BENCHMARK")
    print("=" * 70)

    # Check CUDA
    print(f"\n[1/5] Checking GPU...")
    print(f"  PyTorch Version: {torch.__version__}")
    print(f"  CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  Compute Capability: sm_{torch.cuda.get_device_capability(0)[0]}{torch.cuda.get_device_capability(0)[1]}")

    # Audio info
    print(f"\n[2/5] Audio File Info...")
    audio_path = os.path.join('audio', audio_file)
    if not os.path.exists(audio_path):
        print(f"  [ERROR] File not found: {audio_path}")
        return

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    duration = get_audio_duration(audio_path)

    print(f"  File: {audio_file}")
    print(f"  Size: {file_size_mb:.2f} MB")
    if duration:
        print(f"  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

    # Load model
    print(f"\n[3/5] Loading Whisper Model...")
    print(f"  Model: {model_size}")
    print(f"  Device: cuda")
    print(f"  Compute Type: {compute_type}")

    start_load = time.time()
    model = WhisperModel(model_size, device="cuda", compute_type=compute_type)
    load_time = time.time() - start_load
    print(f"  Model loaded in {load_time:.2f}s")

    # Transcribe
    print(f"\n[4/5] Transcribing...")
    start_transcribe = time.time()

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    # Collect segments
    segment_list = list(segments)
    transcribe_time = time.time() - start_transcribe

    # Results
    print(f"\n[5/5] Results...")
    print(f"  Detected Language: {info.language} (confidence: {info.language_probability:.2%})")
    print(f"  Segments: {len(segment_list)}")
    print(f"  Transcription Time: {transcribe_time:.2f}s")

    if duration:
        speed_factor = duration / transcribe_time
        print(f"  Audio Duration: {duration:.1f}s")
        print(f"  Speed Factor: {speed_factor:.2f}x realtime")
        print(f"  Time per minute: {transcribe_time / (duration/60):.1f}s")

    # Sample output
    print(f"\n  Sample Transcription:")
    for i, segment in enumerate(segment_list[:3]):
        print(f"    [{segment.start:.1f}s - {segment.end:.1f}s] {segment.text}")
        if i >= 2:
            break

    if len(segment_list) > 3:
        print(f"    ... ({len(segment_list) - 3} more segments)")

    # Performance analysis
    print("\n" + "=" * 70)
    print("PERFORMANCE ANALYSIS")
    print("=" * 70)

    if duration:
        # Expected performance for RTX 5080
        expected_time = duration / 6  # ~6x realtime expected
        performance_pct = (expected_time / transcribe_time) * 100

        print(f"\n  Expected Time (RTX 5080): ~{expected_time:.1f}s (6x realtime)")
        print(f"  Actual Time: {transcribe_time:.1f}s ({speed_factor:.1f}x realtime)")
        print(f"  Performance: {performance_pct:.0f}% of expected")

        if performance_pct >= 80:
            print(f"  Status: [EXCELLENT] GPU working optimally!")
        elif performance_pct >= 60:
            print(f"  Status: [GOOD] GPU working well")
        elif performance_pct >= 40:
            print(f"  Status: [OK] GPU working but could be better")
        else:
            print(f"  Status: [WARNING] Performance lower than expected")

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    import sys

    # Default test file
    test_file = "WhatsApp Audio 2025-11-20 at 13.52.25_10f90732.waptt.opus"

    # Allow custom file from command line
    if len(sys.argv) > 1:
        test_file = sys.argv[1]

    try:
        benchmark_transcription(test_file, model_size='tiny', compute_type='float16')
    except Exception as e:
        print(f"\n[ERROR] Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
