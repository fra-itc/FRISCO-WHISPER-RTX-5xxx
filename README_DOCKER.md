# Docker Setup for Frisco Whisper RTX 5xxx

![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![CUDA](https://img.shields.io/badge/CUDA-12.6+-orange.svg)
![NVIDIA](https://img.shields.io/badge/NVIDIA-Container%20Toolkit-green.svg)

Complete Docker containerization for the Whisper transcription application with full NVIDIA GPU support optimized for RTX 5xxx series.

> **⚠️ RTX 5080 Update**: Now uses CUDA 12.6 and PyTorch 2.5.1+ for full sm_120 compute capability support.

---

## Overview

This Docker setup provides:

- **Production-ready containerization** with NVIDIA GPU acceleration
- **Multi-stage builds** for optimized image size
- **CUDA 12.6+ support** for RTX 5xxx series with sm_120
- **PyTorch 2.5.1+** with full RTX 5080 compatibility
- **Automatic dependency management**
- **Security hardening** with non-root user
- **Persistent storage** for models, audio, and transcripts
- **Helper scripts** for simplified operations

### Image Specifications

- **Base Image**: `nvidia/cuda:12.6.0-runtime-ubuntu22.04`
- **Python Version**: 3.10
- **CUDA Version**: 12.6
- **PyTorch**: 2.5.1+ with cu126
- **Image Size**: ~8-10 GB (after build)
- **GPU Support**: NVIDIA RTX 5xxx series (5080, 5090) with sm_120

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
   - Version 560+ for CUDA 12.6 and RTX 5080 (sm_120)
   - Verify: `nvidia-smi`

### System Requirements

- **GPU**: NVIDIA RTX 5080/5090 (16-24GB VRAM)
- **RAM**: 16GB minimum
- **Disk Space**: 20GB free space (for images and models)
- **OS**: Linux, Windows (with WSL2), macOS (Intel only)

---

For complete documentation, see the full README_DOCKER.md file in your repository.
