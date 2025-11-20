#!/bin/bash

###############################################################################
# Docker Build Script for Frisco Whisper RTX 5xxx
# Description: Builds the Docker image with CUDA support
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
DOCKERFILE="$PROJECT_ROOT/Dockerfile"

###############################################################################
# Functions
###############################################################################

print_banner() {
    echo -e "${CYAN}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  FRISCO WHISPER RTX - Docker Build Script"
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

    # Check if NVIDIA Container Toolkit is installed (for GPU support)
    if ! docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_warning "NVIDIA Container Toolkit might not be properly configured."
        print_warning "GPU support may not work. Install nvidia-container-toolkit for GPU acceleration."
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "NVIDIA Container Toolkit detected"
    fi

    # Check if Dockerfile exists
    if [ ! -f "$DOCKERFILE" ]; then
        print_error "Dockerfile not found at: $DOCKERFILE"
        exit 1
    fi

    print_success "All prerequisites checked"
}

build_image() {
    print_info "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
    print_info "Build context: $PROJECT_ROOT"

    cd "$PROJECT_ROOT"

    # Build with BuildKit for better caching and performance
    DOCKER_BUILDKIT=1 docker build \
        --file "$DOCKERFILE" \
        --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
        --target production \
        --progress=plain \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        .

    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
    else
        print_error "Docker build failed"
        exit 1
    fi
}

show_image_info() {
    print_info "Image information:"
    docker images "${IMAGE_NAME}:${IMAGE_TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
}

cleanup_dangling() {
    print_info "Cleaning up dangling images..."
    docker image prune -f > /dev/null
    print_success "Cleanup completed"
}

###############################################################################
# Main
###############################################################################

main() {
    print_banner

    # Parse arguments
    NO_CACHE=false
    CLEANUP=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-cache)
                NO_CACHE=true
                shift
                ;;
            --cleanup)
                CLEANUP=true
                shift
                ;;
            --tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --no-cache    Build without using cache"
                echo "  --cleanup     Remove dangling images after build"
                echo "  --tag TAG     Set custom image tag (default: latest)"
                echo "  --help        Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Check prerequisites
    check_prerequisites

    # Build image
    if [ "$NO_CACHE" = true ]; then
        print_info "Building without cache..."
        DOCKER_BUILDKIT=1 docker build --no-cache -f "$DOCKERFILE" -t "${IMAGE_NAME}:${IMAGE_TAG}" "$PROJECT_ROOT"
    else
        build_image
    fi

    # Show image info
    echo ""
    show_image_info

    # Cleanup if requested
    if [ "$CLEANUP" = true ]; then
        echo ""
        cleanup_dangling
    fi

    echo ""
    print_success "Build process completed!"
    print_info "Next steps:"
    echo "  1. Run with docker-compose: docker-compose up"
    echo "  2. Run with helper script:  ./scripts/docker-run.sh"
    echo "  3. Run manually:            docker run --gpus all -it ${IMAGE_NAME}:${IMAGE_TAG}"
}

main "$@"
