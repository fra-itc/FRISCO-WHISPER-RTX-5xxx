#!/bin/bash

###############################################################################
# Docker Run Script for Frisco Whisper RTX 5xxx
# Description: Runs the Docker container with GPU support
# Author: fra-itc
# Version: 1.0
###############################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="frisco-whisper-rtx"
IMAGE_TAG="latest"
CONTAINER_NAME="whisper-transcribe-gpu"

###############################################################################
# Functions
###############################################################################

print_banner() {
    echo -e "${CYAN}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  FRISCO WHISPER RTX - Docker Run Script"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi

    # Check if image exists
    if ! docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" &> /dev/null; then
        print_error "Docker image not found: ${IMAGE_NAME}:${IMAGE_TAG}"
        print_info "Build the image first using: ./scripts/docker-build.sh"
        exit 1
    fi

    print_success "All prerequisites checked"
}

stop_existing_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Stopping and removing existing container: ${CONTAINER_NAME}"
        docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true
        docker rm "${CONTAINER_NAME}" > /dev/null 2>&1 || true
        print_success "Existing container removed"
    fi
}

create_directories() {
    print_info "Ensuring required directories exist..."
    mkdir -p "$PROJECT_ROOT/audio"
    mkdir -p "$PROJECT_ROOT/transcripts"
    mkdir -p "$PROJECT_ROOT/logs"
    print_success "Directories ready"
}

run_container() {
    local mode=$1
    local gpu_flag=""
    local container_suffix=""

    if [ "$mode" = "gpu" ]; then
        gpu_flag="--gpus all"
        container_suffix="-gpu"
        print_info "Running container with GPU support"
    elif [ "$mode" = "cpu" ]; then
        gpu_flag=""
        container_suffix="-cpu"
        CONTAINER_NAME="whisper-transcribe-cpu"
        print_warning "Running container in CPU-only mode"
    else
        print_error "Invalid mode: $mode"
        exit 1
    fi

    docker run \
        $gpu_flag \
        --rm \
        -it \
        --name "${CONTAINER_NAME}" \
        -v "$PROJECT_ROOT/audio:/app/audio:rw" \
        -v "$PROJECT_ROOT/transcripts:/app/transcripts:rw" \
        -v "$PROJECT_ROOT/logs:/app/logs:rw" \
        -v whisper-model-cache:/app/models:rw \
        -e CUDA_VISIBLE_DEVICES=0 \
        -e NVIDIA_VISIBLE_DEVICES=all \
        -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
        -e PYTHONUNBUFFERED=1 \
        -e OMP_NUM_THREADS=8 \
        -e MKL_NUM_THREADS=8 \
        "${IMAGE_NAME}:${IMAGE_TAG}"
}

run_with_compose() {
    print_info "Running with docker-compose..."
    cd "$PROJECT_ROOT"
    docker-compose up
}

show_help() {
    cat << EOF
Usage: $0 [MODE] [OPTIONS]

Modes:
  gpu               Run with GPU support (default)
  cpu               Run with CPU only (no GPU)
  compose           Run using docker-compose
  shell             Run interactive shell in container
  test              Test GPU availability
  logs              Show container logs

Options:
  --help            Show this help message

Examples:
  $0                # Run with GPU (default)
  $0 gpu            # Run with GPU explicitly
  $0 cpu            # Run with CPU only
  $0 compose        # Run with docker-compose
  $0 shell          # Open shell in container
  $0 test           # Test GPU availability

EOF
}

run_shell() {
    print_info "Opening interactive shell in container..."
    docker run \
        --gpus all \
        --rm \
        -it \
        --name "${CONTAINER_NAME}-shell" \
        -v "$PROJECT_ROOT/audio:/app/audio:rw" \
        -v "$PROJECT_ROOT/transcripts:/app/transcripts:rw" \
        -v "$PROJECT_ROOT/logs:/app/logs:rw" \
        -v whisper-model-cache:/app/models:rw \
        --entrypoint /bin/bash \
        "${IMAGE_NAME}:${IMAGE_TAG}"
}

test_gpu() {
    print_info "Testing GPU availability in container..."
    docker run \
        --gpus all \
        --rm \
        "${IMAGE_NAME}:${IMAGE_TAG}" \
        python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

    if [ $? -eq 0 ]; then
        print_success "GPU test completed successfully"
    else
        print_error "GPU test failed"
        exit 1
    fi
}

show_logs() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker logs -f "${CONTAINER_NAME}"
    else
        print_error "Container ${CONTAINER_NAME} is not running"
        exit 1
    fi
}

###############################################################################
# Main
###############################################################################

main() {
    print_banner

    # Parse arguments
    MODE="${1:-gpu}"

    case "$MODE" in
        --help)
            show_help
            exit 0
            ;;
        gpu)
            check_prerequisites
            create_directories
            stop_existing_container
            run_container "gpu"
            ;;
        cpu)
            check_prerequisites
            create_directories
            stop_existing_container
            run_container "cpu"
            ;;
        compose)
            check_prerequisites
            create_directories
            run_with_compose
            ;;
        shell)
            check_prerequisites
            create_directories
            run_shell
            ;;
        test)
            check_prerequisites
            test_gpu
            ;;
        logs)
            show_logs
            ;;
        *)
            print_error "Unknown mode: $MODE"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
