#!/usr/bin/env python3
"""
GPU Manager Module - Comprehensive GPU Detection and Management

This module provides centralized GPU management for CUDA operations,
including detection, memory management, device selection, and fallback strategies.

Features:
- Multi-GPU detection and enumeration
- CUDA capability testing
- Memory management and monitoring
- Automatic device selection
- Compute type recommendations
- Fallback strategies (GPU -> CPU)
- Cache management

Example:
    gpu_manager = GPUManager()

    # Auto-select best GPU
    device_id = gpu_manager.select_best_gpu()

    # Get GPU information
    info = gpu_manager.get_gpu_info(device_id)

    # Recommend compute type
    compute_type = gpu_manager.recommend_compute_type(device_id)

    # Clear CUDA cache
    gpu_manager.clear_cache()
"""

import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """Detailed information about a GPU device."""
    device_id: int
    name: str
    total_memory_gb: float
    available_memory_gb: float
    cuda_capability: Tuple[int, int]
    cuda_version: Optional[str] = None
    available: bool = True
    supported_compute_types: List[str] = field(default_factory=list)
    recommended_compute_type: Optional[str] = None
    pci_bus_id: Optional[str] = None
    multi_processor_count: Optional[int] = None
    clock_rate_mhz: Optional[int] = None


@dataclass
class MemoryInfo:
    """GPU memory usage information."""
    device_id: int
    total_gb: float
    allocated_gb: float
    reserved_gb: float
    free_gb: float
    utilization_percent: float


class GPUManager:
    """
    Comprehensive GPU Manager for CUDA operations.

    Handles GPU detection, selection, testing, and memory management
    for transcription workloads.

    Attributes:
        available_gpus: List of available GPU device IDs
        has_cuda: Whether CUDA is available on the system
        torch_available: Whether PyTorch is installed
    """

    # Compute type preferences (ordered by performance for RTX cards)
    COMPUTE_TYPE_PREFERENCE = ['float16', 'int8_float32', 'int8', 'float32']

    # Fallback configurations for model loading
    FALLBACK_CONFIGS = [
        {'compute': 'float16', 'device': 'cuda'},
        {'compute': 'float32', 'device': 'cuda'},
        {'compute': 'int8_float32', 'device': 'cuda'},
        {'compute': 'int8', 'device': 'cuda'},
        {'compute': 'float32', 'device': 'cpu'}
    ]

    def __init__(self, auto_initialize: bool = True):
        """
        Initialize GPU Manager.

        Args:
            auto_initialize: Automatically detect GPUs on initialization
        """
        self.torch_available = False
        self.has_cuda = False
        self.available_gpus: List[int] = []
        self._gpu_cache: Dict[int, GPUInfo] = {}

        if auto_initialize:
            self._initialize_cuda()

    def _initialize_cuda(self) -> None:
        """Initialize CUDA and detect available GPUs."""
        try:
            import torch
            self.torch_available = True
            self.has_cuda = torch.cuda.is_available()

            if self.has_cuda:
                self.available_gpus = list(range(torch.cuda.device_count()))
                logger.info(f"Detected {len(self.available_gpus)} CUDA device(s)")
            else:
                logger.warning("CUDA is not available on this system")

        except ImportError:
            logger.warning("PyTorch not installed - GPU features disabled")
        except Exception as e:
            logger.error(f"Error initializing CUDA: {e}")

    def detect_gpus(self) -> List[int]:
        """
        Detect all available GPU devices.

        Returns:
            List of GPU device IDs
        """
        if not self.has_cuda:
            return []

        return self.available_gpus.copy()

    def get_gpu_info(self, device_id: int = 0) -> Optional[GPUInfo]:
        """
        Get detailed information about a specific GPU.

        Args:
            device_id: GPU device ID (default: 0)

        Returns:
            GPUInfo object with GPU details, or None if not available
        """
        # Return cached info if available
        if device_id in self._gpu_cache:
            return self._gpu_cache[device_id]

        if not self.has_cuda or device_id not in self.available_gpus:
            return None

        try:
            import torch

            # Get device properties
            props = torch.cuda.get_device_properties(device_id)
            total_memory_gb = props.total_memory / (1024**3)

            # Get current memory usage
            if hasattr(torch.cuda, 'mem_get_info'):
                free_mem, total_mem = torch.cuda.mem_get_info(device_id)
                available_memory_gb = free_mem / (1024**3)
            else:
                available_memory_gb = total_memory_gb

            # Get CUDA capability
            cuda_capability = (props.major, props.minor)

            # Get CUDA version
            cuda_version = torch.version.cuda

            # Create GPU info
            info = GPUInfo(
                device_id=device_id,
                name=torch.cuda.get_device_name(device_id),
                total_memory_gb=total_memory_gb,
                available_memory_gb=available_memory_gb,
                cuda_capability=cuda_capability,
                cuda_version=cuda_version,
                available=True,
                multi_processor_count=getattr(props, 'multi_processor_count', None),
                clock_rate_mhz=getattr(props, 'clock_rate', 0) // 1000 if hasattr(props, 'clock_rate') else None
            )

            # Test supported compute types
            info.supported_compute_types = self._test_compute_types(device_id)
            info.recommended_compute_type = self.recommend_compute_type(device_id)

            # Cache the result
            self._gpu_cache[device_id] = info

            return info

        except Exception as e:
            logger.error(f"Error getting GPU info for device {device_id}: {e}")
            return None

    def _test_compute_types(self, device_id: int) -> List[str]:
        """
        Test which compute types are supported by the GPU.

        Args:
            device_id: GPU device ID

        Returns:
            List of supported compute types
        """
        supported = []

        try:
            from faster_whisper import WhisperModel

            # Test each compute type
            for compute_type in ['float16', 'int8', 'int8_float32', 'float32']:
                try:
                    # Try to load a tiny model with this compute type
                    test_model = WhisperModel(
                        'tiny',
                        device='cuda',
                        device_index=device_id,
                        compute_type=compute_type
                    )
                    supported.append(compute_type)
                    del test_model

                    # Clear cache after test
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

                except Exception as e:
                    logger.debug(f"Compute type {compute_type} not supported on device {device_id}: {e}")

        except ImportError:
            logger.warning("faster-whisper not installed - cannot test compute types")
        except Exception as e:
            logger.error(f"Error testing compute types: {e}")

        return supported

    def recommend_compute_type(self, device_id: int = 0) -> Optional[str]:
        """
        Recommend optimal compute type for a GPU.

        Args:
            device_id: GPU device ID

        Returns:
            Recommended compute type string, or None if no GPU
        """
        if not self.has_cuda or device_id not in self.available_gpus:
            return 'float32'  # CPU fallback

        try:
            info = self.get_gpu_info(device_id)

            if not info or not info.supported_compute_types:
                return 'float32'

            # Choose from preference order
            for compute_type in self.COMPUTE_TYPE_PREFERENCE:
                if compute_type in info.supported_compute_types:
                    return compute_type

            # Fallback to first supported type
            return info.supported_compute_types[0] if info.supported_compute_types else 'float32'

        except Exception as e:
            logger.error(f"Error recommending compute type: {e}")
            return 'float32'

    def test_gpu(self, device_id: int = 0) -> bool:
        """
        Test if a GPU can be used for transcription.

        Args:
            device_id: GPU device ID to test

        Returns:
            True if GPU works, False otherwise
        """
        if not self.has_cuda or device_id not in self.available_gpus:
            return False

        try:
            from faster_whisper import WhisperModel
            import torch

            # Try to load a tiny model
            test_model = WhisperModel(
                'tiny',
                device='cuda',
                device_index=device_id,
                compute_type='float32'
            )

            # Clean up
            del test_model
            torch.cuda.empty_cache()

            return True

        except Exception as e:
            logger.error(f"GPU test failed for device {device_id}: {e}")
            return False

    def get_memory_info(self, device_id: int = 0) -> Optional[MemoryInfo]:
        """
        Get current memory usage for a GPU.

        Args:
            device_id: GPU device ID

        Returns:
            MemoryInfo object with memory statistics
        """
        if not self.has_cuda or device_id not in self.available_gpus:
            return None

        try:
            import torch

            # Get memory info
            allocated = torch.cuda.memory_allocated(device_id) / (1024**3)
            reserved = torch.cuda.memory_reserved(device_id) / (1024**3)

            if hasattr(torch.cuda, 'mem_get_info'):
                free_mem, total_mem = torch.cuda.mem_get_info(device_id)
                total = total_mem / (1024**3)
                free = free_mem / (1024**3)
            else:
                props = torch.cuda.get_device_properties(device_id)
                total = props.total_memory / (1024**3)
                free = total - allocated

            utilization = ((total - free) / total * 100) if total > 0 else 0.0

            return MemoryInfo(
                device_id=device_id,
                total_gb=total,
                allocated_gb=allocated,
                reserved_gb=reserved,
                free_gb=free,
                utilization_percent=utilization
            )

        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return None

    def clear_cache(self, device_id: Optional[int] = None) -> bool:
        """
        Clear CUDA memory cache.

        Args:
            device_id: Specific device to clear, or None for all devices

        Returns:
            True if successful, False otherwise
        """
        if not self.has_cuda:
            return False

        try:
            import torch

            if device_id is not None:
                with torch.cuda.device(device_id):
                    torch.cuda.empty_cache()
            else:
                torch.cuda.empty_cache()

            logger.info(f"Cleared CUDA cache for device {device_id if device_id is not None else 'all'}")
            return True

        except Exception as e:
            logger.error(f"Error clearing CUDA cache: {e}")
            return False

    def select_best_gpu(self) -> Optional[int]:
        """
        Automatically select the best available GPU.

        Selection criteria (in order):
        1. Most available memory
        2. Highest CUDA capability
        3. Lowest device ID

        Returns:
            Device ID of best GPU, or None if no GPU available
        """
        if not self.has_cuda or not self.available_gpus:
            return None

        best_gpu = None
        best_score = -1

        for device_id in self.available_gpus:
            info = self.get_gpu_info(device_id)

            if not info:
                continue

            # Calculate score based on available memory and CUDA capability
            memory_score = info.available_memory_gb
            capability_score = info.cuda_capability[0] * 10 + info.cuda_capability[1]

            # Combined score (memory is weighted higher)
            score = memory_score * 10 + capability_score

            if score > best_score:
                best_score = score
                best_gpu = device_id

        return best_gpu if best_gpu is not None else (self.available_gpus[0] if self.available_gpus else None)

    def set_device(self, device_id: int) -> bool:
        """
        Set the current CUDA device.

        Args:
            device_id: GPU device ID to set as current

        Returns:
            True if successful, False otherwise
        """
        if not self.has_cuda or device_id not in self.available_gpus:
            return False

        try:
            import torch
            torch.cuda.set_device(device_id)
            logger.info(f"Set CUDA device to {device_id}")
            return True

        except Exception as e:
            logger.error(f"Error setting CUDA device: {e}")
            return False

    def get_fallback_configs(self) -> List[Dict[str, str]]:
        """
        Get list of fallback configurations for model loading.

        Returns:
            List of configuration dictionaries with 'device' and 'compute' keys
        """
        return self.FALLBACK_CONFIGS.copy()

    def get_device_name(self, device_id: int = 0) -> Optional[str]:
        """
        Get the name of a GPU device.

        Args:
            device_id: GPU device ID

        Returns:
            Device name string, or None if not available
        """
        info = self.get_gpu_info(device_id)
        return info.name if info else None

    def print_gpu_summary(self) -> None:
        """Print a formatted summary of all available GPUs."""
        if not self.has_cuda:
            print("No CUDA GPUs available")
            return

        print(f"\nGPU Summary ({len(self.available_gpus)} device(s) found):")
        print("=" * 80)

        for device_id in self.available_gpus:
            info = self.get_gpu_info(device_id)

            if not info:
                continue

            print(f"\nDevice {device_id}: {info.name}")
            print(f"  Memory: {info.available_memory_gb:.2f} GB / {info.total_memory_gb:.2f} GB")
            print(f"  CUDA Capability: {info.cuda_capability[0]}.{info.cuda_capability[1]}")
            print(f"  Supported Compute Types: {', '.join(info.supported_compute_types)}")
            print(f"  Recommended Compute Type: {info.recommended_compute_type}")

            if info.multi_processor_count:
                print(f"  Multi-Processors: {info.multi_processor_count}")
            if info.clock_rate_mhz:
                print(f"  Clock Rate: {info.clock_rate_mhz} MHz")

        print("=" * 80)

    def __repr__(self) -> str:
        """String representation of GPUManager."""
        return (f"GPUManager(has_cuda={self.has_cuda}, "
                f"devices={len(self.available_gpus)})")


# Convenience functions for quick access

def get_default_device() -> str:
    """
    Get default device (cuda if available, else cpu).

    Returns:
        Device string ('cuda' or 'cpu')
    """
    manager = GPUManager()
    return 'cuda' if manager.has_cuda else 'cpu'


def get_recommended_compute_type(device_id: int = 0) -> str:
    """
    Get recommended compute type for a device.

    Args:
        device_id: GPU device ID

    Returns:
        Recommended compute type string
    """
    manager = GPUManager()
    return manager.recommend_compute_type(device_id) or 'float32'


def print_gpu_info() -> None:
    """Print GPU information summary."""
    manager = GPUManager()
    manager.print_gpu_summary()


def test_gpu_available() -> bool:
    """
    Test if GPU is available and working.

    Returns:
        True if GPU is available and functional
    """
    manager = GPUManager()
    if not manager.has_cuda:
        return False

    device_id = manager.select_best_gpu()
    return manager.test_gpu(device_id) if device_id is not None else False
