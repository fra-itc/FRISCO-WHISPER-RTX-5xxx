# Quick Start Guide - Frisco Whisper RTX Web Server

## Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Jinja2 (templates)
- WebSockets (real-time updates)
- Python-multipart (file uploads)

## Starting the Server

### Option 1: Simple Start
```bash
python src/ui/web_server.py
```

Server starts at: **http://localhost:8000**

### Option 2: With Custom Options
```bash
# Custom host and port
python src/ui/web_server.py --host 0.0.0.0 --port 8080

# Development mode with auto-reload
python src/ui/web_server.py --reload

# Production with multiple workers
python src/ui/web_server.py --workers 4
```

## Using the Web Interface

### 1. Access the Web UI
Open browser: **http://localhost:8000**

### 2. Upload Audio File
- Drag-and-drop or click "Select File"
- Supported formats: MP3, WAV, M4A, MP4, AAC, FLAC, OPUS
- Max size: 500 MB

### 3. Configure Transcription
- **Model Size**: large-v3 (recommended for RTX 5080)
- **Task Type**: Transcribe (keep language) or Translate (to English)
- **Language**: Auto-detect or specify
- **Advanced Options** (optional):
  - Beam Size: 5 (default)
  - VAD Filter: Enabled (recommended)

### 4. Start Transcription
Click "Start Transcription" button

### 5. Monitor Progress
- Automatically redirected to Jobs page
- Real-time progress updates via WebSocket
- Status: pending → processing → completed

### 6. Download Result
Click download button to get SRT file

## Using the REST API

### Upload and Transcribe
```bash
# 1. Upload file
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@audio.mp3"

# Response: {"file_path": "/path/to/file", ...}

# 2. Start transcription
curl -X POST http://localhost:8000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/file",
    "model_size": "large-v3",
    "task_type": "transcribe",
    "language": "it"
  }'

# Response: {"job_id": "...", "status": "pending", ...}

# 3. Check status
curl http://localhost:8000/api/v1/jobs/{job_id}

# 4. Download result
curl http://localhost:8000/api/v1/jobs/{job_id}/result -o result.srt
```

## API Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Upload page |
| GET | `/jobs` | Jobs management page |
| POST | `/api/v1/upload` | Upload audio file |
| POST | `/api/v1/transcribe` | Create transcription job |
| GET | `/api/v1/jobs` | List all jobs |
| GET | `/api/v1/jobs/{id}` | Get job details |
| DELETE | `/api/v1/jobs/{id}` | Delete job |
| GET | `/api/v1/jobs/{id}/result` | Download SRT file |
| GET | `/api/v1/system/status` | System info |
| GET | `/api/v1/models` | Available models |
| WS | `/ws/jobs/{id}` | Real-time updates |

## Features

✅ **Drag-and-drop file upload**
✅ **Real-time progress via WebSocket**
✅ **GPU acceleration (RTX 5080)**
✅ **Multiple model sizes**
✅ **Job management and monitoring**
✅ **RESTful API**
✅ **Interactive API documentation**
✅ **Modern Matrix-themed UI**
✅ **Mobile responsive design**
✅ **Background job processing**

## Directory Structure

```
src/ui/
├── web_server.py       # FastAPI application (650+ lines)
├── __init__.py         # Module initialization
├── templates/          # HTML templates
│   ├── base.html      # Base template
│   ├── index.html     # Upload page
│   └── jobs.html      # Jobs page
└── static/            # Static assets
    ├── css/
    │   └── style.css  # Stylesheet (800+ lines)
    └── js/
        └── app.js     # JavaScript (700+ lines)
```

## Troubleshooting

**Server won't start?**
```bash
# Check if FastAPI is installed
pip install fastapi uvicorn

# Verify Python version (3.10+ recommended)
python --version
```

**GPU not detected?**
```bash
# Check CUDA
nvidia-smi

# Check PyTorch CUDA support
python -c "import torch; print(torch.cuda.is_available())"
```

**Upload fails?**
- Check file format (must be audio)
- Check file size (max 500MB)
- Verify disk space

## Production Deployment

For production, use Gunicorn:
```bash
pip install gunicorn

gunicorn src.ui.web_server:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300
```

## Next Steps

1. Read full documentation: `WEB_SERVER_USAGE.md`
2. Explore API docs: http://localhost:8000/docs
3. Test with sample audio files
4. Configure for production deployment

## Support

For detailed documentation, see `WEB_SERVER_USAGE.md`

---

**Version**: 1.3.0
**Last Updated**: November 20, 2025
