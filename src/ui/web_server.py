#!/usr/bin/env python3
"""
FRISCO WHISPER RTX 5xxx - Web Server
FastAPI-based web interface for transcription management
"""

import os
import sys
import time
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, WebSocket, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.transcription import TranscriptionEngine, AudioConverter, GPUInfo
from src.core.transcription_service import TranscriptionService
from src.data.database import DatabaseManager
from src.data.transcript_manager import TranscriptManager
from src.data.file_manager import FileManager
from src.data.format_converters import FormatConverter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db_manager: Optional[DatabaseManager] = None
transcription_service: Optional[TranscriptionService] = None
transcript_manager: Optional[TranscriptManager] = None
file_manager: Optional[FileManager] = None
active_websockets: Dict[str, List[WebSocket]] = {}

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

TRANSCRIPTS_DIR = Path("transcripts")
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.mp4', '.aac', '.flac', '.opus'}


# Pydantic models for request/response
class TranscriptionRequest(BaseModel):
    """Request model for transcription"""
    file_path: str
    model_size: str = Field(default='large-v3', pattern='^(tiny|base|small|medium|large|large-v2|large-v3)$')
    task_type: str = Field(default='transcribe', pattern='^(transcribe|translate)$')
    language: Optional[str] = None
    beam_size: int = Field(default=5, ge=1, le=10)
    vad_filter: bool = True


class JobResponse(BaseModel):
    """Response model for job information"""
    job_id: str
    status: str
    file_name: str
    model_size: str
    created_at: str
    updated_at: Optional[str] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None


class SystemStatusResponse(BaseModel):
    """Response model for system status"""
    gpu_available: bool
    gpu_name: Optional[str] = None
    vram_gb: Optional[float] = None
    cuda_version: Optional[str] = None
    recommended_compute_type: Optional[str] = None
    available_models: List[str]
    upload_dir: str
    transcripts_dir: str
    db_path: str


class JobStatistics(BaseModel):
    """Response model for job statistics"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    processing_jobs: int
    pending_jobs: int
    avg_processing_time: Optional[float] = None
    total_audio_duration: Optional[float] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global db_manager, transcription_service, transcript_manager, file_manager

    # Startup
    logger.info("Starting Frisco Whisper RTX Web Server...")

    # Initialize database
    db_manager = DatabaseManager('database/transcription.db')
    logger.info("Database initialized")

    # Initialize transcription service (integrates all components)
    transcription_service = TranscriptionService(
        db_path='database/transcription.db',
        model_size='large-v3'
    )
    logger.info(f"Transcription service initialized")

    # Initialize managers for direct access
    transcript_manager = TranscriptManager(db_manager)
    file_manager = FileManager(db_manager)
    logger.info("Managers initialized")

    # Log that we're ready (GPU info available via API)
    logger.info("Server ready - GPU info available via /api/v1/system/status")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if transcription_service:
        transcription_service.close()
    if db_manager:
        db_manager.close()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Frisco Whisper RTX 5xxx",
    description="Production-ready transcription web interface with GPU acceleration",
    version="1.3.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ============================================================================
# Web Pages (HTML Templates)
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page with upload interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    """Job management page"""
    return templates.TemplateResponse("jobs.html", {"request": request})


# ============================================================================
# API Endpoints - File Upload
# ============================================================================

@app.post("/api/v1/upload", response_model=Dict[str, str])
async def upload_file(file: UploadFile = File(...)):
    """
    Upload audio file for transcription.

    Returns:
        Dict with file_path and file_name
    """
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Generate unique filename
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}_{file.filename}"
        file_path = UPLOAD_DIR / safe_filename

        # Read and validate file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"File uploaded: {safe_filename} ({len(content)} bytes)")

        return {
            "file_path": str(file_path.absolute()),
            "file_name": file.filename,
            "size_bytes": len(content)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================================================
# API Endpoints - Transcription Jobs
# ============================================================================

@app.post("/api/v1/transcribe", response_model=JobResponse)
async def create_transcription(
    request: TranscriptionRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new transcription job.
    Job will be processed in the background.
    """
    try:
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Get audio duration
        try:
            duration = TranscriptionEngine._get_audio_duration(file_path)
        except Exception:
            duration = None

        # Get compute type and device from transcription service engine
        # Engine is lazy-loaded, so access it to get current config
        try:
            compute_type = transcription_service.engine.compute_type
            device = transcription_service.engine.device
        except Exception as e:
            logger.warning(f"Could not get engine config, using defaults: {e}")
            compute_type = "float16"
            device = "cuda"

        # Create job in database
        job_id = db_manager.create_job(
            file_path=str(file_path),
            model_size=request.model_size,
            task_type=request.task_type,
            language=request.language,
            compute_type=compute_type,
            device=device,
            beam_size=request.beam_size,
            duration_seconds=duration
        )

        # Start transcription in background
        background_tasks.add_task(
            process_transcription,
            job_id=job_id,
            file_path=str(file_path),
            model_size=request.model_size,
            task_type=request.task_type,
            language=request.language,
            beam_size=request.beam_size,
            vad_filter=request.vad_filter
        )

        logger.info(f"Transcription job created: {job_id}")

        return JobResponse(
            job_id=job_id,
            status="pending",
            file_name=file_path.name,
            model_size=request.model_size,
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create transcription job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs", response_model=List[Dict[str, Any]])
async def get_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Get list of transcription jobs with pagination.

    Args:
        status: Filter by status (pending, processing, completed, failed)
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
    """
    try:
        if status:
            jobs = db_manager.get_jobs_by_status(status, limit=limit + offset)
            jobs = jobs[offset:]
        else:
            jobs = db_manager.get_recent_jobs(limit=limit + offset)
            jobs = jobs[offset:]

        return jobs

    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/{job_id}", response_model=Dict[str, Any])
async def get_job(job_id: str):
    """Get detailed job information"""
    try:
        job = db_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its results"""
    try:
        success = db_manager.delete_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")

        logger.info(f"Job deleted: {job_id}")
        return {"message": "Job deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/{job_id}/result")
async def download_result(job_id: str):
    """Download SRT file for completed job"""
    try:
        job = db_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job['status'] != 'completed':
            raise HTTPException(status_code=400, detail="Job not completed yet")

        srt_path = job.get('srt_path')
        if not srt_path or not Path(srt_path).exists():
            raise HTTPException(status_code=404, detail="SRT file not found")

        return FileResponse(
            path=srt_path,
            media_type='text/plain',
            filename=Path(srt_path).name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Endpoints - System Information
# ============================================================================

@app.get("/api/v1/models", response_model=List[str])
async def get_models():
    """Get list of available Whisper models"""
    return TranscriptionEngine.AVAILABLE_MODELS


@app.get("/api/v1/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get system health and GPU status"""
    try:
        # Use a temporary engine to check GPU without loading model
        temp_engine = TranscriptionEngine(model_size='large-v3')
        gpu_info = temp_engine.get_gpu_info()
        temp_engine.cleanup()
    except Exception as e:
        logger.warning(f"Could not get GPU info: {e}")
        gpu_info = None

    return SystemStatusResponse(
        gpu_available=gpu_info.available if gpu_info else False,
        gpu_name=gpu_info.device_name if gpu_info else None,
        vram_gb=gpu_info.vram_gb if gpu_info else None,
        cuda_version=gpu_info.cuda_version if gpu_info else None,
        recommended_compute_type=gpu_info.recommended_compute_type if gpu_info else None,
        available_models=TranscriptionEngine.AVAILABLE_MODELS,
        upload_dir=str(UPLOAD_DIR.absolute()),
        transcripts_dir=str(TRANSCRIPTS_DIR.absolute()),
        db_path=str(db_manager.db_path) if db_manager else "N/A"
    )


@app.get("/api/v1/system/statistics", response_model=JobStatistics)
async def get_statistics():
    """Get job statistics"""
    try:
        stats = db_manager.get_statistics()
        return JobStatistics(**stats)
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Endpoints - Transcript Export
# ============================================================================

@app.get("/api/v1/transcripts/{transcript_id}")
async def get_transcript(transcript_id: int, version: Optional[int] = None):
    """
    Get transcript with segments.

    Args:
        transcript_id: Transcript database ID
        version: Optional version number
    """
    try:
        transcript = transcript_manager.get_transcript(transcript_id, version)
        return transcript
    except Exception as e:
        logger.error(f"Failed to get transcript: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/transcripts/{transcript_id}/versions")
async def get_transcript_versions(transcript_id: int):
    """Get all versions for a transcript"""
    try:
        versions = transcript_manager.get_versions(transcript_id)
        return {"transcript_id": transcript_id, "versions": versions}
    except Exception as e:
        logger.error(f"Failed to get transcript versions: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/v1/transcripts/{transcript_id}/export")
async def export_transcript(
    transcript_id: int,
    format_name: str = Query(..., pattern='^(srt|vtt|json|txt|csv)$'),
    version: Optional[int] = None
):
    """
    Export transcript to specified format.

    Args:
        transcript_id: Transcript database ID
        format_name: Output format (srt, vtt, json, txt, csv)
        version: Optional version number

    Returns:
        File download response
    """
    try:
        # Get transcript to determine filename
        transcript = transcript_manager.get_transcript(transcript_id, version)
        job = db_manager.get_job(transcript['job_id'])

        base_name = Path(job['file_path']).stem if job else f"transcript_{transcript_id}"
        output_filename = f"{base_name}_v{transcript['version_number']}.{format_name}"

        # Export to temporary file
        temp_dir = Path("temp_exports")
        temp_dir.mkdir(exist_ok=True)
        output_path = temp_dir / output_filename

        # Generate export content
        content = transcript_manager.export_transcript(
            transcript_id=transcript_id,
            format_name=format_name,
            output_path=str(output_path),
            version=version
        )

        # Determine media type
        media_types = {
            'srt': 'text/plain',
            'vtt': 'text/vtt',
            'json': 'application/json',
            'txt': 'text/plain',
            'csv': 'text/csv'
        }

        media_type = media_types.get(format_name, 'text/plain')

        return FileResponse(
            path=str(output_path),
            media_type=media_type,
            filename=output_filename,
            headers={"Content-Disposition": f"attachment; filename={output_filename}"}
        )

    except Exception as e:
        logger.error(f"Failed to export transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/transcripts/job/{job_id}")
async def get_transcript_by_job(job_id: str):
    """Get transcript for a specific job"""
    try:
        transcript = transcript_manager.get_transcript_by_job(job_id)
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found for this job")
        return transcript
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transcript by job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket - Real-time Progress Updates
# ============================================================================

@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.
    Sends progress updates during transcription.
    """
    await websocket.accept()

    # Register websocket for this job
    if job_id not in active_websockets:
        active_websockets[job_id] = []
    active_websockets[job_id].append(websocket)

    try:
        # Send initial status
        job = db_manager.get_job(job_id)
        if job:
            await websocket.send_json({
                "type": "status",
                "status": job['status'],
                "job_id": job_id
            })

        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for ping or client messages
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Send pong response
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
    finally:
        # Unregister websocket
        if job_id in active_websockets:
            active_websockets[job_id].remove(websocket)
            if not active_websockets[job_id]:
                del active_websockets[job_id]


async def broadcast_progress(job_id: str, data: Dict[str, Any]):
    """Broadcast progress update to all connected clients for a job"""
    if job_id in active_websockets:
        disconnected = []
        for ws in active_websockets[job_id]:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send progress update: {e}")
                disconnected.append(ws)

        # Remove disconnected websockets
        for ws in disconnected:
            active_websockets[job_id].remove(ws)


# ============================================================================
# Background Tasks - Transcription Processing
# ============================================================================

async def process_transcription(
    job_id: str,
    file_path: str,
    model_size: str,
    task_type: str,
    language: Optional[str],
    beam_size: int,
    vad_filter: bool
):
    """
    Process transcription job in background using TranscriptionService.
    Updates job status and sends progress via WebSocket.
    """
    try:
        # Update job status to processing
        db_manager.update_job(
            job_id=job_id,
            status='processing',
            started_at=datetime.now()
        )

        await broadcast_progress(job_id, {
            "type": "status",
            "status": "processing",
            "message": "Transcription started"
        })

        # Progress callback that broadcasts to WebSocket
        def progress_callback(data: Dict[str, Any]):
            stage = data.get('stage', 'transcription')

            if stage == 'conversion':
                asyncio.create_task(broadcast_progress(job_id, {
                    "type": "progress",
                    "stage": "conversion",
                    "progress_pct": data.get('progress_pct', 0),
                    "message": data.get('message', 'Converting audio...')
                }))
            elif stage == 'transcription':
                asyncio.create_task(broadcast_progress(job_id, {
                    "type": "progress",
                    "stage": "transcription",
                    "segment_number": data.get('segment_number', 0),
                    "progress_pct": data.get('progress_pct', 0),
                    "text": data.get('text', '')
                }))

        # Use TranscriptionService for integrated workflow
        result = transcription_service.transcribe_file(
            file_path=file_path,
            model_size=model_size,
            task=task_type,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            output_dir=str(TRANSCRIPTS_DIR),
            progress_callback=progress_callback,
            skip_duplicate_check=True  # Already uploaded
        )

        if result['success']:
            await broadcast_progress(job_id, {
                "type": "status",
                "status": "completed",
                "message": f"Transcription completed: {result['segments_count']} segments",
                "transcript_id": result['transcript_id'],
                "output_path": result['output_path']
            })

            logger.info(
                f"Job completed: {job_id} "
                f"({result['segments_count']} segments, {result['processing_time_seconds']:.2f}s)"
            )
        else:
            await broadcast_progress(job_id, {
                "type": "status",
                "status": "failed",
                "error": result.get('error', 'Unknown error')
            })

            logger.error(f"Job failed: {job_id}")

    except Exception as e:
        logger.error(f"Job processing error: {e}")

        # Update job as failed
        db_manager.update_job(
            job_id=job_id,
            status='failed',
            error_message=str(e),
            completed_at=datetime.now()
        )

        await broadcast_progress(job_id, {
            "type": "status",
            "status": "failed",
            "error": str(e)
        })


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.3.0"
    }


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the web server"""
    import argparse

    parser = argparse.ArgumentParser(description="Frisco Whisper RTX Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")

    args = parser.parse_args()

    print("=" * 80)
    print("FRISCO WHISPER RTX 5xxx - Web Server v1.3.0")
    print("=" * 80)
    print(f"\nStarting server at http://{args.host}:{args.port}")
    print(f"Swagger UI: http://{args.host}:{args.port}/docs")
    print(f"ReDoc: http://{args.host}:{args.port}/redoc")
    print("\nPress CTRL+C to stop the server")
    print("=" * 80 + "\n")

    uvicorn.run(
        "src.ui.web_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="info"
    )


if __name__ == "__main__":
    main()
