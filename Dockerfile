# Multi-stage Dockerfile for Whisper Transcription with NVIDIA GPU support
# Optimized for RTX 5xxx series (CUDA 12.6+ required for sm_120 support)

# Stage 1: Base image with CUDA runtime
FROM nvidia/cuda:12.6.0-runtime-ubuntu22.04 AS base

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Set timezone
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-dev \
    ffmpeg \
    git \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Stage 2: Dependencies installation
FROM base AS dependencies

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install PyTorch with CUDA support
# Using CUDA 12.6 index for RTX 5080 (sm_120) compatibility
RUN pip3 install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu126

# Install other Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Stage 3: Production image
FROM base AS production

# Set working directory
WORKDIR /app

# Copy Python packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Create non-root user for security
RUN groupadd -r whisper && useradd -r -g whisper -u 1000 whisper

# Create necessary directories with proper permissions
RUN mkdir -p /app/audio /app/transcripts /app/logs /app/models && \
    chown -R whisper:whisper /app

# Copy application files
COPY --chown=whisper:whisper whisper_transcribe_frisco.py .
COPY --chown=whisper:whisper requirements.txt .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV OMP_NUM_THREADS=8
ENV MKL_NUM_THREADS=8

# Set model cache directory (to persist downloaded models)
ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models

# Switch to non-root user
USER whisper

# Health check (validates Python and GPU availability)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" || exit 1

# Volume mounts for data persistence
VOLUME ["/app/audio", "/app/transcripts", "/app/logs", "/app/models"]

# Default command: run interactive menu
CMD ["python3", "whisper_transcribe_frisco.py"]

# Labels for metadata
LABEL maintainer="fra-itc"
LABEL description="Whisper Transcription optimized for NVIDIA RTX 5xxx"
LABEL version="1.2"
LABEL cuda.version="12.6"
LABEL gpu.arch="RTX 5xxx series"
