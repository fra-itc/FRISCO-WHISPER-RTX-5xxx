# TranscriptionEngine - Quick Start Guide

## Installation

The TranscriptionEngine is already part of your project. Just import and use!

```python
from src.core import TranscriptionEngine
```

## 5-Second Example

```python
from src.core import transcribe_file

result = transcribe_file('audio.wav', model_size='large-v3', language='it')
print(f"Done! {result.output_path}")
```

## Common Use Cases

### 1. Transcribe a Single File

```python
from src.core import TranscriptionEngine

# Initialize engine
engine = TranscriptionEngine(model_size='large-v3')

# Transcribe
result = engine.transcribe('audio/myfile.wav', language='it')

if result.success:
    print(f"Success! Saved to: {result.output_path}")
    print(f"Segments: {result.segments_count}")
    print(f"Language: {result.language} ({result.language_probability:.2%})")
else:
    print(f"Error: {result.error}")
```

### 2. Auto-Detect Language

```python
# Don't specify language - it will be auto-detected
result = engine.transcribe('audio/myfile.wav', language=None)

print(f"Detected language: {result.language}")
```

### 3. Translate to English

```python
result = engine.transcribe(
    'audio/italian_audio.wav',
    task='translate',  # Translate to English
    language='it'      # Source language
)
```

### 4. Batch Processing

```python
from pathlib import Path
from src.core import TranscriptionEngine

# Get all audio files
audio_dir = Path('audio')
audio_files = list(audio_dir.glob('*.wav'))

# Process all with one model instance (faster!)
with TranscriptionEngine(model_size='large-v3') as engine:
    for audio_file in audio_files:
        result = engine.transcribe(str(audio_file))
        print(f"✓ {audio_file.name}: {result.segments_count} segments")
```

### 5. Real-Time Progress

```python
def show_progress(data):
    segment = data['segment_number']
    text = data['text']
    progress = data['progress_pct']
    print(f"[{progress:.1f}%] Segment {segment}: {text[:50]}...")

engine = TranscriptionEngine(model_size='large-v3')
result = engine.transcribe(
    'audio/long_file.wav',
    progress_callback=show_progress
)
```

### 6. Convert Audio Format First

```python
from src.core import AudioConverter, TranscriptionEngine

# Convert M4A/MP3 to WAV
converter = AudioConverter()
wav_path = converter.convert_to_wav('audio/podcast.m4a')

# Then transcribe
engine = TranscriptionEngine(model_size='large-v3')
result = engine.transcribe(wav_path)

# Clean up WAV
wav_path.unlink()
```

### 7. Check GPU Capabilities

```python
from src.core import test_gpu

gpu_info = test_gpu()

if gpu_info.available:
    print(f"GPU: {gpu_info.device_name}")
    print(f"VRAM: {gpu_info.vram_gb:.1f} GB")
    print(f"Recommended compute type: {gpu_info.recommended_compute_type}")
else:
    print("No GPU available - will use CPU")
```

### 8. Custom Configuration

```python
from src.core import TranscriptionEngine

# Manually configure everything
engine = TranscriptionEngine(
    model_size='medium',
    device='cuda',
    compute_type='float16',
    auto_detect_gpu=False
)

result = engine.transcribe(
    audio_path='audio/file.wav',
    task='transcribe',
    language='it',
    beam_size=10,           # Higher = more accurate, slower
    vad_filter=True,        # Filter silence
    word_timestamps=True    # Word-level timing
)
```

## Model Sizes

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| tiny | 40 MB | Fastest | Lowest | Testing |
| base | 75 MB | Very Fast | Low | Quick drafts |
| small | 460 MB | Fast | Good | General use |
| medium | 1.5 GB | Moderate | High | Balanced |
| large-v3 | 3 GB | Slower | Best | Production, RTX 5080 |

## Compute Types

| Type | Speed | Quality | GPU Required | Best For |
|------|-------|---------|--------------|----------|
| float16 | Fastest | Excellent | Yes (RTX) | RTX 30xx/40xx/50xx |
| int8 | Very Fast | Very Good | Yes | Older GPUs |
| float32 | Moderate | Excellent | Optional | Universal |

## Context Manager (Recommended)

Always use context manager for automatic cleanup:

```python
with TranscriptionEngine(model_size='large-v3') as engine:
    result = engine.transcribe('audio.wav')
    # Model automatically cleaned up here
```

Or manually:
```python
engine = TranscriptionEngine(model_size='large-v3')
result = engine.transcribe('audio.wav')
engine.cleanup()  # Don't forget this!
```

## Error Handling

```python
result = engine.transcribe('audio.wav')

if result.success:
    # Success
    print(f"Output: {result.output_path}")
else:
    # Error occurred
    print(f"Error: {result.error}")
```

## Retry on Failure

```python
# Automatically retry up to 3 times
result = engine.transcribe_with_retry(
    'difficult_audio.wav',
    max_retries=3
)
```

## Performance Tips

1. **Reuse Engine for Multiple Files**: Load model once, transcribe many times
2. **Use Context Manager**: Automatic cleanup prevents memory leaks
3. **Use float16 on RTX GPUs**: Fastest compute type for modern NVIDIA cards
4. **Enable VAD Filter**: Removes silence, speeds up processing
5. **Choose Right Model**: Don't use large-v3 if medium is good enough

## Output Format

The engine outputs SRT subtitle format:

```srt
1
00:00:00,000 --> 00:00:03,500
This is the first segment of text.

2
00:00:03,500 --> 00:00:08,100
This is the second segment of text.
```

## Integration Examples

### Flask API
```python
from flask import Flask, request
from src.core import TranscriptionEngine

app = Flask(__name__)
engine = TranscriptionEngine(model_size='large-v3')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    audio = request.files['audio']
    result = engine.transcribe(audio.filename)
    return {'success': result.success, 'path': str(result.output_path)}
```

### Command Line Script
```python
#!/usr/bin/env python3
import sys
from src.core import transcribe_file

if len(sys.argv) < 2:
    print("Usage: transcribe.py <audio_file>")
    sys.exit(1)

result = transcribe_file(sys.argv[1], model_size='large-v3')
print(f"Done: {result.output_path}")
```

## Troubleshooting

### GPU Not Detected
```python
# Check CUDA availability
import torch
print(f"CUDA available: {torch.cuda.is_available()}")

# Test GPU
from src.core import test_gpu
gpu_info = test_gpu()
print(f"GPU available: {gpu_info.available}")
```

### Out of Memory
```python
# Try smaller model
engine = TranscriptionEngine(model_size='medium')

# Or use int8
engine = TranscriptionEngine(model_size='large-v3', compute_type='int8')

# Or use CPU
engine = TranscriptionEngine(model_size='large-v3', device='cpu')
```

### Slow Processing
```python
# Make sure GPU is being used
engine = TranscriptionEngine(model_size='large-v3')
print(f"Using device: {engine.device}")
print(f"Compute type: {engine.compute_type}")

# Should see: device=cuda, compute_type=float16
```

## More Examples

See `examples/basic_usage.py` for 8 complete working examples.

## Documentation

- Full architecture: `docs/ARCHITECTURE.md`
- This quick start: `docs/QUICK_START.md`
- Code examples: `examples/basic_usage.py`
- API reference: See docstrings in `src/core/transcription.py`

## Support

For issues or questions, check:
1. GPU detection: Run `test_gpu()` function
2. Audio format: Use AudioConverter if not WAV 16kHz mono
3. Model loading: Check disk space and internet for first download
4. Memory issues: Try smaller model or int8 compute type

## Next Steps

1. Try the examples: `python examples/basic_usage.py`
2. Run a test transcription
3. Check GPU status with `test_gpu()`
4. Read the full architecture docs
5. Build your own application!
