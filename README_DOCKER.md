# Docker Setup for Frisco Whisper RTX 5xxx

![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![CUDA](https://img.shields.io/badge/CUDA-12.1+-orange.svg)
![NVIDIA](https://img.shields.io/badge/NVIDIA-Container%20Toolkit-green.svg)

Complete Docker containerization for the Whisper transcription application with full NVIDIA GPU support optimized for RTX 5xxx series.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Usage](#usage)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

---

## Overview

This Docker setup provides:

- **Production-ready containerization** with NVIDIA GPU acceleration
- **Multi-stage builds** for optimized image size
- **CUDA 12.1+ support** for RTX 5xxx series
- **Automatic dependency management**
- **Security hardening** with non-root user
- **Persistent storage** for models, audio, and transcripts
- **Helper scripts** for simplified operations

### Image Specifications

- **Base Image**: `nvidia/cuda:12.1.0-runtime-ubuntu22.04`
- **Python Version**: 3.10
- **CUDA Version**: 12.1
- **Image Size**: ~8-10 GB (after build)
- **GPU Support**: NVIDIA RTX 5xxx series (5080, 5090)

---

## Prerequisites

### Required Software

1. **Docker Engine** 20.10+
   - [Install Docker](https://docs.docker.com/engine/install/)
   - Verify: `docker --version`

2. **NVIDIA Container Toolkit**
   - Required for GPU support
   - [Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

3. **Docker Compose** v2.0+ (optional but recommended)
   - Usually included with Docker Desktop
   - Verify: `docker-compose --version`

4. **NVIDIA GPU Drivers**
   - Version 525+ for CUDA 12.1
   - Verify: `nvidia-smi`

### System Requirements

- **GPU**: NVIDIA RTX 5080/5090 (16-24GB VRAM)
- **RAM**: 16GB minimum
- **Disk Space**: 20GB free space (for images and models)
- **OS**: Linux, Windows (with WSL2), macOS (Intel only)

---

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Build the image
docker-compose build

# 2. Run the container
docker-compose up

# 3. Stop the container
docker-compose down
```

### Option 2: Using Helper Scripts

```bash
# 1. Build the image
./scripts/docker-build.sh

# 2. Run with GPU support
./scripts/docker-run.sh gpu

# 3. Test GPU availability
./scripts/docker-run.sh test
```

### Option 3: Manual Docker Commands

```bash
# 1. Build the image
docker build -t frisco-whisper-rtx:latest .

# 2. Run the container
docker run --gpus all -it \
  -v $(pwd)/audio:/app/audio \
  -v $(pwd)/transcripts:/app/transcripts \
  frisco-whisper-rtx:latest
```

---

## Detailed Setup

### Step 1: Install NVIDIA Container Toolkit

**Ubuntu/Debian:**

```bash
# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install the toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test the installation
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

**Windows (WSL2):**

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/install/)
2. Enable WSL2 backend
3. Install NVIDIA drivers for WSL2
4. GPU support is automatically configured

### Step 2: Build the Docker Image

```bash
# Using the helper script (recommended)
./scripts/docker-build.sh

# Options:
./scripts/docker-build.sh --no-cache    # Build without cache
./scripts/docker-build.sh --cleanup     # Clean up after build
./scripts/docker-build.sh --tag v1.2    # Custom tag
```

**Build Output:**

```
═══════════════════════════════════════════════════════════════
  FRISCO WHISPER RTX - Docker Build Script
═══════════════════════════════════════════════════════════════
[INFO] Checking prerequisites...
[SUCCESS] NVIDIA Container Toolkit detected
[SUCCESS] All prerequisites checked
[INFO] Building Docker image: frisco-whisper-rtx:latest
...
[SUCCESS] Docker image built successfully
```

### Step 3: Verify the Build

```bash
# Check image size and details
docker images frisco-whisper-rtx

# Test GPU availability
./scripts/docker-run.sh test

# Expected output:
# CUDA Available: True
# GPU: NVIDIA GeForce RTX 5080
```

---

## Usage

### Basic Transcription Workflow

1. **Place audio files** in the `audio/` directory
2. **Run the container**
3. **Select transcription option** from the menu
4. **Find results** in the `transcripts/` directory

### Running Modes

#### 1. Interactive Mode with GPU

```bash
./scripts/docker-run.sh gpu
```

This launches the interactive menu where you can:
- Transcribe audio files
- Translate to Italian
- Batch process multiple files
- Test GPU performance

#### 2. CPU-Only Mode

```bash
./scripts/docker-run.sh cpu
```

Runs without GPU acceleration (slower, for testing/fallback).

#### 3. Docker Compose Mode

```bash
# Start in foreground (interactive)
docker-compose up

# Start in background (detached)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

#### 4. Shell Access

```bash
# Open bash shell in container
./scripts/docker-run.sh shell

# Or manually
docker run --gpus all -it --rm \
  -v $(pwd)/audio:/app/audio \
  frisco-whisper-rtx:latest /bin/bash
```

### Volume Mounts

The container uses the following volume mounts:

| Host Directory | Container Directory | Purpose |
|----------------|---------------------|---------|
| `./audio/` | `/app/audio/` | Input audio files |
| `./transcripts/` | `/app/transcripts/` | Output SRT files |
| `./logs/` | `/app/logs/` | Application logs |
| Named volume | `/app/models/` | Cached AI models |

### Environment Variables

Configure the container behavior with environment variables:

```yaml
# In docker-compose.yml or -e flags
CUDA_VISIBLE_DEVICES=0              # GPU device ID
OMP_NUM_THREADS=8                   # CPU thread count
HF_HOME=/app/models                 # Model cache directory
PYTHONUNBUFFERED=1                  # Real-time output
```

---

## Architecture

### Multi-Stage Build

```
Stage 1 (base)         → System dependencies, Python, FFmpeg
Stage 2 (dependencies) → PyTorch + CUDA, Python packages
Stage 3 (production)   → Minimal runtime with app code
```

**Benefits:**
- Smaller final image size
- Better layer caching
- Faster rebuilds
- Cleaner dependency management

### Directory Structure

```
FRISCO-WHISPER-RTX-5xxx/
├── Dockerfile                # Multi-stage build definition
├── docker-compose.yml        # Compose configuration
├── .dockerignore            # Excluded files
├── requirements.txt         # Python dependencies
├── scripts/
│   ├── docker-build.sh     # Build helper script
│   └── docker-run.sh       # Run helper script
├── audio/                   # Input files (volume)
├── transcripts/             # Output files (volume)
├── logs/                    # Log files (volume)
└── whisper_transcribe_frisco.py
```

### Security Features

- **Non-root user**: Application runs as user `whisper` (UID 1000)
- **Read-only where possible**: Only necessary directories are writable
- **No new privileges**: Security option enabled
- **Minimal attack surface**: Only required packages installed

---

## Configuration

### Dockerfile Customization

Edit `Dockerfile` to customize:

```dockerfile
# Change Python version
FROM python:3.11-slim  # Instead of 3.10

# Change CUDA version
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Adjust resource limits
ENV OMP_NUM_THREADS=16  # More CPU threads
```

### Docker Compose Customization

Edit `docker-compose.yml` to customize:

```yaml
# Port mapping (for future web UI)
ports:
  - "8000:8000"

# Resource limits
deploy:
  resources:
    limits:
      memory: 16g
      cpus: '8'

# Use specific GPU
environment:
  - CUDA_VISIBLE_DEVICES=1  # Use GPU 1 instead of 0
```

### Model Selection

Models are automatically downloaded and cached in the persistent volume.

**Available models:**
- `small` (~460 MB) - Fast, less accurate
- `medium` (~1.5 GB) - Balanced (default)
- `large-v3` (~3 GB) - Best quality

Change via the interactive menu (option 5).

---

## Troubleshooting

### GPU Not Detected

**Problem:** Container can't access GPU

**Solution:**

```bash
# 1. Check host GPU
nvidia-smi

# 2. Test NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# 3. Verify container toolkit
nvidia-ctk --version

# 4. Restart Docker daemon
sudo systemctl restart docker
```

### Out of Memory

**Problem:** CUDA out of memory error

**Solutions:**

1. **Use smaller model:**
   ```bash
   # Select 'small' instead of 'large-v3' in menu
   ```

2. **Limit VRAM usage:**
   ```bash
   # Only use specific GPU
   docker run -e CUDA_VISIBLE_DEVICES=0 ...
   ```

3. **Close other GPU applications:**
   ```bash
   # Check GPU usage
   nvidia-smi
   ```

### Build Failures

**Problem:** Docker build fails

**Solutions:**

```bash
# 1. Clear build cache
docker builder prune -a

# 2. Rebuild without cache
./scripts/docker-build.sh --no-cache

# 3. Check disk space
df -h

# 4. Update base images
docker pull nvidia/cuda:12.1.0-runtime-ubuntu22.04
```

### Permission Denied

**Problem:** Can't write to output directories

**Solutions:**

```bash
# 1. Check directory permissions
ls -la audio/ transcripts/

# 2. Fix permissions
chmod -R 755 audio/ transcripts/ logs/

# 3. Run container with your UID
docker run --user $(id -u):$(id -g) ...
```

### Container Exits Immediately

**Problem:** Container starts and exits

**Solutions:**

```bash
# 1. Check logs
docker logs whisper-transcribe-gpu

# 2. Run with shell to debug
./scripts/docker-run.sh shell

# 3. Check health status
docker inspect --format='{{.State.Health.Status}}' whisper-transcribe-gpu
```

### Slow Transcription

**Problem:** Transcription is slower than expected

**Solutions:**

1. **Verify GPU usage:**
   ```bash
   # In another terminal while transcribing
   watch -n 1 nvidia-smi
   ```

2. **Check compute type:**
   - Use float16 for RTX 5xxx
   - Avoid float32 (slower)

3. **Optimize batch size:**
   - Process multiple files together
   - GPU stays loaded

---

## Advanced Usage

### Custom Entry Point

Run specific commands instead of the interactive menu:

```bash
# Run GPU test only
docker run --gpus all --rm frisco-whisper-rtx:latest \
  python3 -c "import torch; print(torch.cuda.is_available())"

# Run with custom Python script
docker run --gpus all --rm \
  -v $(pwd)/my_script.py:/app/my_script.py \
  frisco-whisper-rtx:latest \
  python3 my_script.py
```

### Multi-GPU Setup

```yaml
# docker-compose.yml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 2  # Use 2 GPUs
          capabilities: [gpu]
```

### CI/CD Integration

```yaml
# .github/workflows/docker.yml
name: Docker Build
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build image
        run: docker build -t frisco-whisper-rtx:${{ github.sha }} .
      - name: Test
        run: docker run --rm frisco-whisper-rtx:${{ github.sha }} python3 --version
```

### Kubernetes Deployment

```yaml
# kubernetes-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whisper-transcribe
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: whisper
        image: frisco-whisper-rtx:latest
        resources:
          limits:
            nvidia.com/gpu: 1
        volumeMounts:
        - name: audio
          mountPath: /app/audio
```

### Performance Optimization

```bash
# Build with specific optimization flags
docker build \
  --build-arg TORCH_CUDA_ARCH_LIST="8.9"  # RTX 5xxx architecture \
  --build-arg CUDA_VISIBLE_DEVICES=0 \
  -t frisco-whisper-rtx:optimized .

# Run with performance flags
docker run --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  frisco-whisper-rtx:optimized
```

---

## Files Reference

### Generated Files

| File | Description |
|------|-------------|
| `Dockerfile` | Multi-stage build definition with CUDA support |
| `docker-compose.yml` | Compose configuration for easy deployment |
| `.dockerignore` | Files excluded from Docker context |
| `requirements.txt` | Python package dependencies |
| `scripts/docker-build.sh` | Helper script to build the image |
| `scripts/docker-run.sh` | Helper script to run the container |
| `README_DOCKER.md` | This documentation |

### Helper Script Commands

**docker-build.sh:**
```bash
./scripts/docker-build.sh              # Standard build
./scripts/docker-build.sh --no-cache   # Force rebuild
./scripts/docker-build.sh --cleanup    # Clean after build
./scripts/docker-build.sh --tag v1.3   # Custom tag
./scripts/docker-build.sh --help       # Show help
```

**docker-run.sh:**
```bash
./scripts/docker-run.sh gpu       # Run with GPU (default)
./scripts/docker-run.sh cpu       # Run CPU-only mode
./scripts/docker-run.sh compose   # Run via docker-compose
./scripts/docker-run.sh shell     # Open interactive shell
./scripts/docker-run.sh test      # Test GPU availability
./scripts/docker-run.sh logs      # View container logs
./scripts/docker-run.sh --help    # Show help
```

---

## Best Practices

### Development Workflow

1. **Build once:** `./scripts/docker-build.sh`
2. **Test GPU:** `./scripts/docker-run.sh test`
3. **Run interactively:** `./scripts/docker-run.sh gpu`
4. **Process files:** Use menu options 1-3
5. **Check output:** Files in `transcripts/`

### Production Deployment

1. **Tag versions:** Use semantic versioning
   ```bash
   docker tag frisco-whisper-rtx:latest frisco-whisper-rtx:1.2.0
   ```

2. **Use compose:** For reproducible deployments
   ```bash
   docker-compose up -d
   ```

3. **Monitor health:** Enable health checks
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

4. **Backup models:** Named volume persists across restarts
   ```bash
   docker volume inspect whisper-model-cache
   ```

### Maintenance

```bash
# Update base images
docker pull nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Rebuild with updates
./scripts/docker-build.sh --no-cache

# Clean up old images
docker image prune -a

# Clean up volumes (careful!)
docker volume prune
```

---

## Support and Contribution

### Getting Help

- **Issues:** Open a [GitHub Issue](https://github.com/fra-itc/FRISCO-WHISPER-RTX-5xxx/issues)
- **Discussions:** Use GitHub Discussions
- **Documentation:** See main [README.md](README.md)

### Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test Docker changes
4. Submit a Pull Request

---

## License

MIT License - See main repository LICENSE file

---

## Credits

- **NVIDIA CUDA** - GPU acceleration
- **Docker** - Containerization platform
- **OpenAI Whisper** - AI transcription model
- **Faster-Whisper** - Optimized implementation

---

**Made with love for RTX 5xxx series**

*FRISCO WHISPER - RULEZ in Docker!*
