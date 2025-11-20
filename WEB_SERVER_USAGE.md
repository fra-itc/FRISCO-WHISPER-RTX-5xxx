# Frisco Whisper RTX - Web Server Usage Guide

## Overview

The Frisco Whisper RTX web server provides a modern, user-friendly web interface for GPU-accelerated audio transcription. Built with FastAPI and featuring real-time WebSocket updates, it offers both a web UI and a RESTful API.

## Features

### Web Interface
- **Drag-and-Drop Upload**: Intuitive file upload with drag-and-drop support
- **Real-time Progress**: WebSocket-based live updates during transcription
- **Job Management**: Monitor, download, and delete transcription jobs
- **GPU Status**: Real-time GPU/CPU status display
- **Responsive Design**: Mobile-friendly, modern Matrix-inspired theme
- **Advanced Options**: Configurable model size, language, beam size, and VAD filter

### REST API
- **File Upload**: `POST /api/v1/upload`
- **Create Transcription**: `POST /api/v1/transcribe`
- **List Jobs**: `GET /api/v1/jobs`
- **Get Job Details**: `GET /api/v1/jobs/{job_id}`
- **Download Result**: `GET /api/v1/jobs/{job_id}/result`
- **Delete Job**: `DELETE /api/v1/jobs/{job_id}`
- **System Status**: `GET /api/v1/system/status`
- **Statistics**: `GET /api/v1/system/statistics`
- **Available Models**: `GET /api/v1/models`

### WebSocket
- **Real-time Updates**: `WS /ws/jobs/{job_id}`
  - Progress updates during transcription
  - Status changes (pending → processing → completed/failed)
  - Segment-by-segment transcription progress

## Installation

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

Required packages:
- `fastapi>=0.109.0` - Web framework
- `uvicorn[standard]>=0.27.0` - ASGI server
- `python-multipart>=0.0.6` - File upload support
- `jinja2>=3.1.2` - Template engine
- `websockets>=12.0` - WebSocket support
- `pydantic>=2.5.0` - Data validation

### 2. Verify Installation

```bash
# Check if FastAPI is installed
python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')"

# Check if Uvicorn is installed
python -c "import uvicorn; print(f'Uvicorn version: {uvicorn.__version__}')"
```

## Running the Web Server

### Basic Usage

```bash
# Run from project root
python -m src.ui.web_server

# Or use the module directly
python src/ui/web_server.py
```

The server will start at: **http://localhost:8000**

### Command-Line Options

```bash
# Custom host and port
python src/ui/web_server.py --host 0.0.0.0 --port 8080

# Enable auto-reload for development
python src/ui/web_server.py --reload

# Multiple workers for production
python src/ui/web_server.py --workers 4
```

### Available Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--host` | `0.0.0.0` | Host address to bind |
| `--port` | `8000` | Port number |
| `--reload` | `False` | Enable auto-reload (development) |
| `--workers` | `1` | Number of worker processes |

### Production Deployment

For production environments, use Gunicorn with Uvicorn workers:

```bash
# Install gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn src.ui.web_server:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile -
```

## Web Interface Usage

### 1. Upload Page (/)

**Features:**
- Drag-and-drop audio file upload
- File format validation (MP3, WAV, M4A, MP4, AAC, FLAC, OPUS)
- Maximum file size: 500 MB
- Upload progress bar

**Transcription Options:**
- **Model Size**: Choose from tiny, base, small, medium, large-v3
- **Task Type**: Transcribe (maintain language) or Translate (to English)
- **Language**: Auto-detect or specify language
- **Advanced Options**:
  - Beam Size (1-10): Higher = more accurate but slower
  - VAD Filter: Voice Activity Detection to filter non-speech

**Workflow:**
1. Upload audio file (drag-and-drop or select)
2. Choose model size and options
3. Click "Start Transcription"
4. Redirected to Jobs page to monitor progress

### 2. Jobs Page (/jobs)

**Features:**
- Real-time job status updates via WebSocket
- Filter jobs by status (pending, processing, completed, failed)
- Search jobs by filename
- Statistics dashboard showing job counts
- Auto-refresh every 10 seconds

**Job Actions:**
- **View Details**: Click eye icon to see full job information
- **Download**: Download SRT file for completed jobs
- **Delete**: Remove job and associated files

**Job Statuses:**
- **Pending** (⏰): Job queued, not started
- **Processing** (🔄): Transcription in progress
- **Completed** (✅): Successfully transcribed
- **Failed** (❌): Error during transcription

### 3. API Documentation

Access interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## REST API Usage

### Upload File

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@audio.mp3"
```

Response:
```json
{
  "file_path": "/path/to/uploads/abc12345_audio.mp3",
  "file_name": "audio.mp3",
  "size_bytes": 5242880
}
```

### Create Transcription Job

```bash
curl -X POST http://localhost:8000/api/v1/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/uploads/abc12345_audio.mp3",
    "model_size": "large-v3",
    "task_type": "transcribe",
    "language": "it",
    "beam_size": 5,
    "vad_filter": true
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "file_name": "audio.mp3",
  "model_size": "large-v3",
  "created_at": "2025-11-20T14:30:00"
}
```

### List Jobs

```bash
# All jobs
curl http://localhost:8000/api/v1/jobs

# Filter by status
curl http://localhost:8000/api/v1/jobs?status=completed

# Pagination
curl http://localhost:8000/api/v1/jobs?limit=20&offset=0
```

### Get Job Details

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "file_name": "audio.mp3",
  "model_size": "large-v3",
  "task_type": "transcribe",
  "language": "it",
  "detected_language": "it",
  "language_probability": 0.99,
  "compute_type": "float16",
  "device": "cuda",
  "segment_count": 42,
  "processing_time_seconds": 12.5,
  "created_at": "2025-11-20T14:30:00",
  "completed_at": "2025-11-20T14:30:12",
  "srt_path": "/path/to/transcripts/audio.srt"
}
```

### Download SRT Result

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/result \
  -o transcription.srt
```

### Delete Job

```bash
curl -X DELETE http://localhost:8000/api/v1/jobs/{job_id}
```

### System Status

```bash
curl http://localhost:8000/api/v1/system/status
```

Response:
```json
{
  "gpu_available": true,
  "gpu_name": "NVIDIA GeForce RTX 5080",
  "vram_gb": 16.0,
  "cuda_version": "12.1",
  "recommended_compute_type": "float16",
  "available_models": ["tiny", "base", "small", "medium", "large-v3", "large-v2"],
  "upload_dir": "/path/to/uploads",
  "transcripts_dir": "/path/to/transcripts",
  "db_path": "database/transcription.db"
}
```

### Statistics

```bash
curl http://localhost:8000/api/v1/system/statistics
```

Response:
```json
{
  "total_jobs": 150,
  "completed_jobs": 142,
  "failed_jobs": 3,
  "processing_jobs": 1,
  "pending_jobs": 4,
  "avg_processing_time": 15.7,
  "total_audio_duration": 7200.5
}
```

## WebSocket Usage

### Connect to Job Progress

```javascript
const jobId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'status') {
    console.log(`Job status: ${data.status}`);
  } else if (data.type === 'progress') {
    console.log(`Progress: ${data.progress_pct}%`);
    console.log(`Segment ${data.segment_number}: ${data.text}`);
  }
};

// Keep connection alive
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send('ping');
  }
}, 15000);
```

### Message Types

**Status Update:**
```json
{
  "type": "status",
  "status": "processing",
  "message": "Transcription started",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Progress Update:**
```json
{
  "type": "progress",
  "stage": "transcription",
  "segment_number": 5,
  "progress_pct": 25.5,
  "text": "This is the transcribed text"
}
```

**Completion:**
```json
{
  "type": "status",
  "status": "completed",
  "message": "Transcription completed: 42 segments",
  "srt_path": "/path/to/transcripts/audio.srt"
}
```

## Directory Structure

```
FRISCO-WHISPER-RTX-5xxx/
├── src/
│   └── ui/
│       ├── __init__.py          # Module initialization
│       ├── web_server.py        # FastAPI application (650+ lines)
│       ├── templates/
│       │   ├── base.html        # Base template with navigation
│       │   ├── index.html       # Upload page
│       │   └── jobs.html        # Job management page
│       └── static/
│           ├── css/
│           │   └── style.css    # Matrix-themed stylesheet
│           └── js/
│               └── app.js       # Client-side JavaScript
├── uploads/                     # Uploaded audio files (auto-created)
├── transcripts/                 # Generated SRT files (auto-created)
├── database/
│   └── transcription.db        # SQLite database
└── requirements.txt            # Updated with FastAPI dependencies
```

## Configuration

### Environment Variables (Optional)

```bash
# Set custom upload directory
export UPLOAD_DIR=/path/to/uploads

# Set custom transcripts directory
export TRANSCRIPTS_DIR=/path/to/transcripts

# Set database path
export DB_PATH=/path/to/database.db

# Set maximum file size (bytes)
export MAX_FILE_SIZE=524288000  # 500MB
```

### CORS Configuration

To allow cross-origin requests from specific domains, edit `src/ui/web_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Server Won't Start

**Issue**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
pip install -r requirements.txt
```

### WebSocket Connection Failed

**Issue**: WebSocket disconnects immediately

**Solution**:
- Ensure firewall allows WebSocket connections
- Check if reverse proxy (nginx/apache) supports WebSocket upgrades
- Verify WebSocket URL uses correct protocol (ws:// or wss://)

### Upload Fails

**Issue**: "File too large" error

**Solution**:
- Check file size (max 500MB)
- Verify disk space in uploads directory
- Increase MAX_FILE_SIZE if needed

### GPU Not Detected

**Issue**: Server shows "CPU Mode" despite having GPU

**Solution**:
1. Check CUDA installation: `nvidia-smi`
2. Verify PyTorch CUDA support: `python -c "import torch; print(torch.cuda.is_available())"`
3. Reinstall PyTorch with CUDA support

### Transcription Fails

**Issue**: Jobs stuck in "processing" or fail immediately

**Solution**:
- Check ffmpeg installation: `ffmpeg -version`
- Verify audio file format is supported
- Check server logs for error messages
- Ensure sufficient VRAM for model size

## Performance Optimization

### Model Selection

| Model | Speed | Accuracy | VRAM | Use Case |
|-------|-------|----------|------|----------|
| tiny | Very Fast | Low | ~1GB | Quick testing |
| base | Fast | Medium | ~1GB | Fast transcription |
| small | Medium | Good | ~2GB | Balanced performance |
| medium | Slow | Very Good | ~5GB | High accuracy |
| large-v3 | Very Slow | Excellent | ~10GB | Best quality |

### Tips for Best Performance

1. **Use GPU**: RTX 5080 recommended for large-v3 model
2. **Enable VAD Filter**: Reduces processing time by skipping silence
3. **Optimize Beam Size**: 5 is balanced; lower for speed, higher for accuracy
4. **Batch Processing**: Process multiple files sequentially
5. **Monitor VRAM**: Use `nvidia-smi` to check GPU memory usage

## Security Considerations

### Production Checklist

- [ ] Enable HTTPS with SSL certificate
- [ ] Configure CORS for specific origins only
- [ ] Set up authentication/authorization
- [ ] Limit file upload size
- [ ] Sanitize file names and paths
- [ ] Rate limit API endpoints
- [ ] Use environment variables for secrets
- [ ] Enable request logging
- [ ] Set up monitoring and alerts
- [ ] Regular security updates

### Recommended Security Headers

Add to FastAPI middleware:
```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

## Support and Resources

- **Project Repository**: [GitHub Link]
- **Issue Tracker**: [GitHub Issues]
- **API Documentation**: http://localhost:8000/docs
- **Whisper Documentation**: https://github.com/openai/whisper
- **Faster-Whisper**: https://github.com/guillaumekln/faster-whisper

## License

This web interface is part of the Frisco Whisper RTX project. See LICENSE file for details.

---

**Version**: 1.3.0
**Last Updated**: November 20, 2025
**Built with**: FastAPI, Uvicorn, Jinja2, WebSockets
