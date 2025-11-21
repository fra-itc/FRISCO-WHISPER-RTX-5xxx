# Quick Start Guide - FRISCO WHISPER RTX 5080

## ✅ What Was Fixed

### 1. Web Server Bug (CRITICAL)
- **Issue**: Undefined `transcription_engine` variable caused crashes
- **Location**: `src/ui/web_server.py:270-271`
- **Status**: ✅ FIXED - Web UI now works!

### 2. CLI Unicode Encoding Issue
- **Issue**: Windows console couldn't display Unicode characters (✓)
- **Location**: `whisper_transcribe_frisco.py:154-160`
- **Status**: ✅ FIXED - CLI menu now displays correctly!

### 3. PyTorch RTX 5080 Compatibility
- **Issue**: PyTorch doesn't natively support sm_120 (shows warnings)
- **Status**: ⚠️ WORKS WITH WARNINGS - GPU acceleration functional!
- **Details**: PyTorch uses backward compatibility (sm_90 mode)
- **Performance**: Slightly reduced but still very fast

## 🚀 How to Use

### Option 1: Web UI (Recommended)

```powershell
# Start the web server
python src/ui/web_server.py

# Or with custom port
python src/ui/web_server.py --port 8001
```

Then open your browser:
- **Main UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Jobs Dashboard**: http://localhost:8000/jobs

**Features**:
- Drag & drop file upload
- Real-time progress tracking
- Job management dashboard
- Multiple format export (SRT, VTT, JSON, TXT, CSV)
- WebSocket live updates

### Option 2: CLI Interactive Menu

```powershell
python whisper_transcribe_frisco.py
```

**Menu Options**:
1. Trascrivi audio (mantiene lingua)
2. Traduci in italiano
3. Batch processing
4. Test GPU
5. Scegli modello (default: large-v3)
0. Esci

### Option 3: Direct Python API

```python
from src.core.transcription_service import TranscriptionService

# Initialize service
service = TranscriptionService(
    db_path='database/transcription.db',
    model_size='large-v3'
)

# Transcribe file
result = service.transcribe_file(
    file_path='audio/myfile.mp3',
    language='it',
    output_dir='transcripts'
)

print(f"Transcript ID: {result['transcript_id']}")
print(f"Output: {result['output_path']}")
```

## 📊 Current System Status

**GPU**: ✅ NVIDIA GeForce RTX 5080 (15.9 GB VRAM)
**CUDA**: ✅ 12.6 (functional)
**PyTorch**: ⚠️ 2.9.1+cu126 (works with sm_90 compatibility)
**Compute Types Supported**:
- ✅ FLOAT32 (compatible universally)
- ✅ FLOAT16 (RECOMMENDED - best for RTX 5080)
- ✅ INT8 (fastest, slight quality reduction)

**Recommended Settings**:
- Model: `large-v3` (best quality)
- Compute: `float16` (optimal speed/quality)
- Beam size: `5` (good balance)

## ⚠️ About PyTorch Warnings

You'll see these warnings when starting:
```
UserWarning: NVIDIA GeForce RTX 5080 with CUDA capability sm_120
is not compatible with the current PyTorch installation.
```

**This is expected and OK!** Your GPU is working via backward compatibility.

### If You Want Full sm_120 Support (Optional)

See `RTX5080_FIX_GUIDE.md` for:
- Custom PyTorch build installation
- PyTorch nightly builds
- Performance comparison

**Note**: Current setup works well, so this is optional optimization.

## 📁 File Locations

```
FRISCO-WHISPER-RTX-5xxx/
├── audio/              # Place audio files here
├── transcripts/        # Output transcripts saved here
├── uploads/            # Web UI uploads
├── database/           # SQLite database
│   └── transcription.db
├── logs/               # Application logs
└── temp_exports/       # Temporary export files
```

## 🎯 Quick Test

### Test CLI:
```powershell
# 1. Place audio file in audio/ folder
# 2. Run CLI
python whisper_transcribe_frisco.py
# 3. Choose option [1] and follow prompts
```

### Test Web UI:
```powershell
# 1. Start server
python src/ui/web_server.py

# 2. Open browser to http://localhost:8000
# 3. Drag & drop audio file
# 4. Click "Start Transcription"
# 5. Watch real-time progress!
```

## 📈 Performance Tips

1. **Use float16**: Best balance for RTX 5080
   ```python
   compute_type='float16'
   ```

2. **Choose right model**:
   - `large-v3`: Best quality (slower) - **RECOMMENDED**
   - `medium`: Good balance
   - `small`: Fast but less accurate

3. **Batch processing**: Use CLI option [3] for multiple files

4. **Close other GPU apps**: Free up VRAM for better performance

## 🔍 Troubleshooting

### Web UI won't start
```powershell
# Check if port is in use
netstat -ano | findstr :8000

# Use different port
python src/ui/web_server.py --port 8001
```

### CLI crashes immediately
```powershell
# Verify dependencies
pip install -r requirements.txt

# Test imports
python -c "from faster_whisper import WhisperModel; print('OK')"
```

### Transcription fails
1. Check audio file format (supported: mp3, wav, m4a, mp4, aac, flac, opus)
2. Try smaller model: `medium` instead of `large-v3`
3. Check disk space
4. Review logs in `logs/` directory

### Out of memory errors
1. Use smaller model (medium or small)
2. Close other GPU applications
3. Reduce batch size for batch processing

## 📚 Documentation

- **Full API**: http://localhost:8000/docs (when server running)
- **Architecture**: `docs/ARCHITECTURE.md`
- **API Design**: `docs/API_DESIGN.md`
- **RTX 5080 Fix**: `RTX5080_FIX_GUIDE.md`

## 🎉 You're Ready!

Everything is working now:
- ✅ Web UI functional
- ✅ CLI menu operational
- ✅ GPU acceleration active
- ✅ All compute types supported

Choose your preferred interface and start transcribing!

For questions or issues, check the logs or refer to the documentation files.

---

**Generated with Claude Code**
Last Updated: 2025-11-20
