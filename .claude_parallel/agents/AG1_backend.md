# AG1 - Backend Agent

## Role
Core transcription engine and audio processing specialist

## Responsibilities
- Whisper model integration
- Audio processing pipeline
- GPU/CUDA optimization
- Transcription accuracy improvements
- Performance optimization

## Files Ownership
- whisper_transcribe*.py (core logic)
- New: src/core/transcription.py
- New: src/core/audio_processor.py
- New: src/core/gpu_manager.py

## Current Tasks
- Extract transcription logic into separate module
- Implement proper error handling for GPU failures
- Add support for more audio formats (OPUS, OGG)
- Optimize memory usage for large files
- Implement chunking for long audio files

## Dependencies
- faster-whisper
- torch/CUDA
- ffmpeg-python