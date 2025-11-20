#!/bin/bash

###############################################################################
# Docker Setup Verification Script
# Description: Verifies all Docker files and prerequisites are in place
# Author: fra-itc
# Version: 1.0
###############################################################################

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_header() {
    echo -e "${CYAN}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Docker Setup Verification"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

check_file() {
    local file="$1"
    local description="$2"

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: ${file##*/}"
        return 0
    else
        echo -e "${RED}✗${NC} $description: ${file##*/} - MISSING"
        return 1
    fi
}

check_executable() {
    local file="$1"
    local description="$2"

    if [ -x "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: ${file##*/} (executable)"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $description: ${file##*/} (not executable)"
        chmod +x "$file" 2>/dev/null && echo -e "  ${GREEN}→${NC} Made executable"
        return 0
    fi
}

print_header

echo -e "\n${CYAN}Checking Docker Files:${NC}"
errors=0

check_file "$PROJECT_ROOT/Dockerfile" "Dockerfile" || ((errors++))
check_file "$PROJECT_ROOT/docker-compose.yml" "Docker Compose" || ((errors++))
check_file "$PROJECT_ROOT/.dockerignore" "Docker Ignore" || ((errors++))
check_file "$PROJECT_ROOT/requirements.txt" "Requirements" || ((errors++))
check_file "$PROJECT_ROOT/README_DOCKER.md" "Docker Documentation" || ((errors++))

echo -e "\n${CYAN}Checking Helper Scripts:${NC}"
check_executable "$PROJECT_ROOT/scripts/docker-build.sh" "Build Script" || ((errors++))
check_executable "$PROJECT_ROOT/scripts/docker-run.sh" "Run Script" || ((errors++))

echo -e "\n${CYAN}Checking Prerequisites:${NC}"

# Docker
if command -v docker &> /dev/null; then
    version=$(docker --version)
    echo -e "${GREEN}✓${NC} Docker installed: $version"
else
    echo -e "${RED}✗${NC} Docker not found"
    ((errors++))
fi

# Docker Compose
if command -v docker-compose &> /dev/null; then
    version=$(docker-compose --version)
    echo -e "${GREEN}✓${NC} Docker Compose installed: $version"
else
    echo -e "${YELLOW}⚠${NC} Docker Compose not found (optional)"
fi

# NVIDIA SMI
if command -v nvidia-smi &> /dev/null; then
    gpu_info=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    echo -e "${GREEN}✓${NC} NVIDIA GPU detected: $gpu_info"
else
    echo -e "${YELLOW}⚠${NC} nvidia-smi not found (GPU support will not work)"
fi

# NVIDIA Container Toolkit
if docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓${NC} NVIDIA Container Toolkit configured"
else
    echo -e "${RED}✗${NC} NVIDIA Container Toolkit not configured"
    echo -e "  ${YELLOW}→${NC} Install: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    ((errors++))
fi

echo -e "\n${CYAN}Checking Directory Structure:${NC}"
for dir in audio transcripts logs; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        echo -e "${GREEN}✓${NC} Directory exists: $dir/"
    else
        echo -e "${YELLOW}⚠${NC} Directory missing: $dir/ - creating..."
        mkdir -p "$PROJECT_ROOT/$dir"
    fi
done

echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"
if [ $errors -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Docker setup is ready.${NC}"
    echo -e "\n${CYAN}Next steps:${NC}"
    echo "  1. Build the image:  ./scripts/docker-build.sh"
    echo "  2. Test GPU:         ./scripts/docker-run.sh test"
    echo "  3. Run application:  ./scripts/docker-run.sh gpu"
    exit 0
else
    echo -e "${RED}Found $errors error(s). Please fix the issues above.${NC}"
    exit 1
fi
