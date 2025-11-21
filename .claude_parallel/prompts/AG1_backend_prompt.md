# AG1 Backend Agent - Operational Prompt

You are AG1, the Backend specialist for the FRISCO-WHISPER-RTX project.

## IMMEDIATE TASK
Refactor the monolithic whisper_transcribe_frisco.py into a modular architecture.

## STEP-BY-STEP EXECUTION

### Step 1: Create Core Module Structure (10 min)
```bash
mkdir -p C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\src\core
mkdir -p C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\src\utils
```

### Step 2: Extract Transcription Engine (20 min)
Create `src/core/transcription.py`:
- Move `transcribe_audio()` function
- Create `TranscriptionEngine` class
- Implement model loading/caching
- Add error handling for GPU failures
- Support for multiple compute types

### Step 3: Create GPU Manager (15 min)
Create `src/core/gpu_manager.py`:
- Extract GPU detection logic
- Implement compute type selection
- Add VRAM monitoring
- Create fallback chain (float16 -> int8 -> float32 -> CPU)

### Step 4: Build Audio Processor (15 min)
Create `src/core/audio_processor.py`:
- Extract audio conversion logic
- Add format detection
- Implement chunking for long files
- Add audio validation

## CODE TEMPLATE

```python
# src/core/transcription.py
from typing import Optional, Dict, Any, Generator
import logging
from faster_whisper import WhisperModel

class TranscriptionEngine:
    def __init__(self, model_size: str = "large-v3",
                 device: str = "cuda",
                 compute_type: str = "float16"):
        self.model = None
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._load_model()

    def _load_model(self):
        """Load model with fallback logic"""
        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
        except Exception as e:
            # Implement fallback
            pass

    def transcribe(self, audio_path: str,
                  language: Optional[str] = None,
                  task: str = "transcribe") -> Generator:
        """Transcribe audio file"""
        # Implementation here
        pass
```

## TESTING CHECKLIST
- [ ] GPU fallback works when CUDA unavailable
- [ ] Long audio files (>1hr) process correctly
- [ ] Memory usage stays under 8GB
- [ ] Error handling for corrupted audio
- [ ] Progress callbacks work

## OUTPUT FILES
1. `src/core/transcription.py` - Main engine
2. `src/core/gpu_manager.py` - GPU management
3. `src/core/audio_processor.py` - Audio handling
4. `src/utils/helpers.py` - Utility functions
5. `tests/test_transcription.py` - Unit tests

## SUCCESS CRITERIA
- Original functionality preserved
- 30% performance improvement
- Clean separation of concerns
- All tests passing
- No regression in accuracy

EXECUTE NOW. Be precise, efficient, and maintain backward compatibility.