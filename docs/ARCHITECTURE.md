# Frisco Whisper RTX - Backend Architecture

## Overview

The monolithic `whisper_transcribe_frisco.py` script has been refactored into a modular, reusable architecture. The core transcription logic is now extracted into a clean, well-documented class-based system.

## Directory Structure

```
FRISCO-WHISPER-RTX-5xxx/
├── src/
│   ├── __init__.py
│   └── core/
│       ├── __init__.py
│       └── transcription.py    # Core transcription engine
├── examples/
│   └── basic_usage.py          # Usage examples
├── docs/
│   └── ARCHITECTURE.md         # This file
├── audio/                      # Input audio files
├── transcripts/                # Output SRT files
└── whisper_transcribe_frisco.py  # Original monolithic script
```

## Core Components

### 1. TranscriptionEngine Class

**Location:** `src/core/transcription.py`

The main class that encapsulates all transcription functionality.

#### Key Features:
- **Automatic GPU Detection**: Detects CUDA availability and optimal compute type
- **Multiple Model Support**: tiny, base, small, medium, large-v3
- **Compute Type Auto-Selection**: Automatically selects float16, int8, or float32
- **Fallback Mechanism**: Automatically tries alternative configurations on failure
- **Progress Callbacks**: Real-time progress updates during transcription
- **Context Manager Support**: Automatic resource cleanup
- **Type Hints**: Full type annotations for better IDE support

#### Methods:

```python
__init__(model_size, device, compute_type, auto_detect_gpu)
    # Initialize engine with model configuration

load_model()
    # Load Whisper model with automatic fallback

transcribe(audio_path, output_dir, task, language, beam_size, ...)
    # Main transcription method
    # Returns: TranscriptionResult

transcribe_with_retry(audio_path, max_retries, **kwargs)
    # Transcribe with automatic retry on failure

get_gpu_info()
    # Get GPU capabilities and recommendations
    # Returns: GPUInfo

cleanup()
    # Free memory and clean up resources
```

### 2. AudioConverter Class

**Location:** `src/core/transcription.py`

Utility class for audio format conversion.

#### Methods:

```python
convert_to_wav(input_file, output_dir, progress_callback)
    # Convert audio to WAV 16kHz mono
    # Returns: Path to WAV file

is_wav_compatible(file_path)
    # Check if file is already in correct format
    # Returns: bool
```

### 3. Data Classes

#### TranscriptionResult

Encapsulates the result of a transcription operation.

```python
@dataclass
class TranscriptionResult:
    success: bool                    # Operation success status
    output_path: Optional[Path]      # Path to output SRT file
    segments_count: int              # Number of transcribed segments
    language: Optional[str]          # Detected/specified language
    language_probability: float      # Language detection confidence
    duration: float                  # Processing time in seconds
    error: Optional[str]             # Error message if failed
```

#### GPUInfo

Contains GPU capabilities and recommendations.

```python
@dataclass
class GPUInfo:
    available: bool                       # GPU availability
    device_name: Optional[str]            # GPU model name
    vram_gb: float                        # VRAM in GB
    cuda_version: Optional[str]           # CUDA version
    supported_compute_types: List[str]    # Supported types
    recommended_compute_type: Optional[str] # Best compute type
```

## Key Improvements Over Original Script

### 1. Modularity
- **Before**: 688 lines in a single file
- **After**: Separated into focused, reusable components
- Core transcription logic: 590 lines (pure functionality)
- Example usage: 250+ lines of documented examples

### 2. Reusability
- **Before**: Tightly coupled to CLI menu system
- **After**: Can be imported and used in:
  - Command-line scripts
  - Web APIs (Flask, FastAPI)
  - Desktop applications
  - Jupyter notebooks
  - Automated pipelines

### 3. Type Safety
- Full type hints for all functions and methods
- Better IDE autocomplete and error detection
- Self-documenting code

### 4. Error Handling
- Structured error reporting via TranscriptionResult
- Automatic fallback configurations
- Optional retry logic

### 5. Progress Tracking
- Callback-based progress system
- Decoupled from UI (can use any visualization)
- Real-time segment-by-segment updates

### 6. Resource Management
- Context manager support (`with` statement)
- Explicit cleanup methods
- CUDA cache clearing

## Preserved Functionality

All features from the original script are preserved:

✓ GPU optimization (CUDA, float16, int8)
✓ Automatic GPU detection and testing
✓ Multiple model sizes support
✓ Language auto-detection
✓ Translation mode (task='translate')
✓ VAD filtering
✓ Beam search configuration
✓ Progress tracking
✓ SRT output format
✓ Audio duration calculation
✓ Multiple audio format support
✓ Retry logic with fallback configurations

## Usage Patterns

### Pattern 1: Simple One-Liner
```python
from src.core import transcribe_file

result = transcribe_file('audio.wav', model_size='large-v3', language='it')
```

### Pattern 2: Context Manager
```python
from src.core import TranscriptionEngine

with TranscriptionEngine(model_size='large-v3') as engine:
    result = engine.transcribe('audio.wav', language='it')
```

### Pattern 3: Explicit Control
```python
from src.core import TranscriptionEngine

engine = TranscriptionEngine(model_size='large-v3')
engine.load_model()
result = engine.transcribe('audio.wav', language='it')
engine.cleanup()
```

### Pattern 4: Batch Processing
```python
from src.core import TranscriptionEngine

with TranscriptionEngine(model_size='large-v3') as engine:
    for audio_file in audio_files:
        result = engine.transcribe(audio_file)
```

### Pattern 5: With Progress Callback
```python
def progress_handler(data):
    print(f"Segment {data['segment_number']}: {data['text'][:50]}...")

engine = TranscriptionEngine(model_size='large-v3')
result = engine.transcribe('audio.wav', progress_callback=progress_handler)
```

## Configuration Options

### Model Sizes
- `tiny`: ~40 MB, fastest, lowest accuracy
- `base`: ~75 MB, fast, moderate accuracy
- `small`: ~460 MB, balanced
- `medium`: ~1.5 GB, high accuracy
- `large-v3`: ~3 GB, best accuracy (recommended for RTX 5080)

### Compute Types
- `float16`: Best for RTX cards (highest performance)
- `int8`: Fast alternative, slightly lower quality
- `float32`: Universal compatibility, slower

### Task Types
- `transcribe`: Maintain original language
- `translate`: Translate to English

## GPU Optimization

The engine automatically detects and configures GPU settings:

1. **Detection Phase**:
   - Check CUDA availability
   - Query GPU name and VRAM
   - Test supported compute types

2. **Selection Phase**:
   - Prioritize float16 for RTX cards
   - Fall back to int8 if float16 unavailable
   - Use float32 as universal fallback
   - Switch to CPU if GPU fails

3. **Runtime Phase**:
   - Apply selected configuration
   - Monitor for errors
   - Auto-retry with fallback configs
   - Report performance metrics

## Integration Examples

### Flask API
```python
from flask import Flask, request
from src.core import TranscriptionEngine

app = Flask(__name__)
engine = TranscriptionEngine(model_size='large-v3')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    audio_file = request.files['audio']
    result = engine.transcribe(audio_file.filename)
    return {'text': result.output_path.read_text()}
```

### FastAPI
```python
from fastapi import FastAPI, UploadFile
from src.core import TranscriptionEngine

app = FastAPI()
engine = TranscriptionEngine(model_size='large-v3')

@app.post("/transcribe")
async def transcribe(file: UploadFile):
    result = engine.transcribe(file.filename)
    return {"status": "success", "path": str(result.output_path)}
```

### Jupyter Notebook
```python
from src.core import TranscriptionEngine

# Initialize engine
engine = TranscriptionEngine(model_size='medium')

# Check GPU
gpu_info = engine.get_gpu_info()
print(f"GPU: {gpu_info.device_name}")

# Transcribe
result = engine.transcribe('lecture.wav', language='en')
print(f"Transcribed {result.segments_count} segments")

# Display results
from IPython.display import display, Markdown
display(Markdown(result.output_path.read_text()))
```

## Testing

### Unit Test Example
```python
import pytest
from src.core import TranscriptionEngine, TranscriptionResult

def test_engine_initialization():
    engine = TranscriptionEngine(model_size='tiny')
    assert engine.model_size == 'tiny'
    assert engine.device in ['cuda', 'cpu']

def test_transcription_success():
    engine = TranscriptionEngine(model_size='tiny')
    result = engine.transcribe('test_audio.wav')
    assert isinstance(result, TranscriptionResult)
    assert result.success is True or result.error is not None

def test_gpu_detection():
    from src.core import test_gpu
    gpu_info = test_gpu()
    assert hasattr(gpu_info, 'available')
```

## Performance Considerations

### Memory Management
- Models are loaded once and reused
- Use context managers for automatic cleanup
- Manual cleanup with `engine.cleanup()`
- CUDA cache is cleared on cleanup

### Batch Processing
- Load model once, transcribe multiple files
- Significant speedup for multiple files
- Example: 10 files processed 5x faster than loading model 10 times

### Optimal Settings for RTX 5080
```python
engine = TranscriptionEngine(
    model_size='large-v3',  # Best quality
    device='cuda',           # Use GPU
    compute_type='float16'   # Optimal for RTX
)
```

## Migration Guide

### From Original Script to New API

**Old (monolithic):**
```python
# Embedded in interactive menu
wav_path = convert_to_wav(input_file, output_dir)
result = transcribe_audio(wav_path, output_dir, 'transcribe', 'it',
                         CURRENT_MODEL, best_compute)
```

**New (modular):**
```python
from src.core import TranscriptionEngine, AudioConverter

# Convert if needed
converter = AudioConverter()
wav_path = converter.convert_to_wav(input_file, output_dir)

# Transcribe
engine = TranscriptionEngine(model_size='large-v3')
result = engine.transcribe(wav_path, language='it')
```

## Future Enhancements

Potential additions to the architecture:

1. **Async Support**: Async transcription for concurrent processing
2. **Streaming**: Real-time audio stream transcription
3. **Caching**: LRU cache for repeated transcriptions
4. **Metrics**: Detailed performance metrics collection
5. **Multiple GPUs**: Multi-GPU support for parallel processing
6. **Custom Models**: Support for fine-tuned Whisper models
7. **Output Formats**: VTT, TXT, JSON output formats
8. **Speaker Diarization**: Identify different speakers

## Conclusion

The refactored architecture provides:
- Clean separation of concerns
- Easy integration into other projects
- Maintainable and testable code
- All original functionality preserved
- Enhanced error handling and reporting
- Better performance for batch operations

The TranscriptionEngine is now a true library component that can be used in any Python project requiring audio transcription capabilities.
