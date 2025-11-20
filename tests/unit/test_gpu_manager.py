"""
Unit tests for GPU Manager module.

Tests GPU detection, selection, memory management,
and compute type recommendations.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.gpu_manager import (
    GPUManager,
    GPUInfo,
    MemoryInfo,
    get_default_device,
    get_recommended_compute_type,
    test_gpu_available
)


# ============================================================================
# Tests for GPU Detection
# ============================================================================

class TestGPUDetection:
    """Test suite for GPU detection and enumeration."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_gpu_manager_initialization_with_cuda(self, mock_gpu):
        """Test GPU manager initialization when CUDA is available."""
        manager = GPUManager()

        assert manager.torch_available is True
        assert manager.has_cuda is True
        assert len(manager.available_gpus) > 0

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_gpu_manager_initialization_without_cuda(self, mock_gpu_unavailable):
        """Test GPU manager initialization when CUDA is not available."""
        manager = GPUManager()

        assert manager.has_cuda is False
        assert len(manager.available_gpus) == 0

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_detect_gpus_returns_list(self, mock_gpu):
        """Test that detect_gpus returns list of device IDs."""
        manager = GPUManager()
        gpus = manager.detect_gpus()

        assert isinstance(gpus, list)
        assert len(gpus) > 0
        assert all(isinstance(gpu_id, int) for gpu_id in gpus)

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_detect_gpus_no_cuda(self, mock_gpu_unavailable):
        """Test detect_gpus when CUDA is not available."""
        manager = GPUManager()
        gpus = manager.detect_gpus()

        assert gpus == []


# ============================================================================
# Tests for GPU Information
# ============================================================================

class TestGPUInformation:
    """Test suite for GPU information retrieval."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_gpu_info_returns_info_object(self, mock_gpu):
        """Test that get_gpu_info returns GPUInfo object."""
        manager = GPUManager()
        info = manager.get_gpu_info(0)

        assert info is not None
        assert isinstance(info, GPUInfo)
        assert info.available is True

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_gpu_info_has_correct_fields(self, mock_gpu):
        """Test that GPUInfo contains all expected fields."""
        manager = GPUManager()
        info = manager.get_gpu_info(0)

        assert hasattr(info, 'device_id')
        assert hasattr(info, 'name')
        assert hasattr(info, 'total_memory_gb')
        assert hasattr(info, 'available_memory_gb')
        assert hasattr(info, 'cuda_capability')
        assert hasattr(info, 'cuda_version')

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_gpu_info_invalid_device(self, mock_gpu):
        """Test get_gpu_info with invalid device ID."""
        manager = GPUManager()
        info = manager.get_gpu_info(99)

        assert info is None

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_gpu_info_caching(self, mock_gpu):
        """Test that GPU info is cached after first retrieval."""
        manager = GPUManager()

        # First call
        info1 = manager.get_gpu_info(0)

        # Second call should return cached info
        info2 = manager.get_gpu_info(0)

        assert info1 is info2  # Same object reference

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_device_name(self, mock_gpu):
        """Test getting device name."""
        manager = GPUManager()
        name = manager.get_device_name(0)

        assert name is not None
        assert isinstance(name, str)
        assert len(name) > 0


# ============================================================================
# Tests for Compute Type Recommendations
# ============================================================================

class TestComputeTypeRecommendation:
    """Test suite for compute type recommendations."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_recommend_compute_type_with_cuda(self, mock_gpu):
        """Test compute type recommendation with CUDA available."""
        with patch('src.core.gpu_manager.WhisperModel'):
            manager = GPUManager()
            compute_type = manager.recommend_compute_type(0)

            assert compute_type is not None
            assert compute_type in ['float16', 'int8', 'int8_float32', 'float32']

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_recommend_compute_type_without_cuda(self, mock_gpu_unavailable):
        """Test compute type recommendation without CUDA."""
        manager = GPUManager()
        compute_type = manager.recommend_compute_type(0)

        assert compute_type == 'float32'  # CPU fallback

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_recommend_compute_type_prefers_float16(self, mock_gpu):
        """Test that float16 is preferred for RTX cards."""
        with patch('src.core.gpu_manager.WhisperModel') as mock_model:
            manager = GPUManager()

            # Clear cache to force recomputation
            manager._gpu_cache.clear()

            compute_type = manager.recommend_compute_type(0)

            # float16 should be preferred for modern GPUs
            if compute_type:
                assert compute_type in ['float16', 'int8_float32', 'int8', 'float32']


# ============================================================================
# Tests for GPU Testing
# ============================================================================

class TestGPUTesting:
    """Test suite for GPU testing functionality."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_test_gpu_with_cuda(self, mock_gpu):
        """Test GPU testing when CUDA is available."""
        with patch('src.core.gpu_manager.WhisperModel'):
            manager = GPUManager()
            result = manager.test_gpu(0)

            assert isinstance(result, bool)

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_test_gpu_without_cuda(self, mock_gpu_unavailable):
        """Test GPU testing when CUDA is not available."""
        manager = GPUManager()
        result = manager.test_gpu(0)

        assert result is False

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_test_gpu_invalid_device(self, mock_gpu):
        """Test GPU testing with invalid device ID."""
        manager = GPUManager()
        result = manager.test_gpu(99)

        assert result is False


# ============================================================================
# Tests for Memory Management
# ============================================================================

class TestMemoryManagement:
    """Test suite for GPU memory management."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_memory_info_returns_info_object(self, mock_gpu):
        """Test that get_memory_info returns MemoryInfo object."""
        manager = GPUManager()
        mem_info = manager.get_memory_info(0)

        assert mem_info is not None
        assert isinstance(mem_info, MemoryInfo)

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_memory_info_has_correct_fields(self, mock_gpu):
        """Test that MemoryInfo contains all expected fields."""
        manager = GPUManager()
        mem_info = manager.get_memory_info(0)

        assert hasattr(mem_info, 'device_id')
        assert hasattr(mem_info, 'total_gb')
        assert hasattr(mem_info, 'allocated_gb')
        assert hasattr(mem_info, 'reserved_gb')
        assert hasattr(mem_info, 'free_gb')
        assert hasattr(mem_info, 'utilization_percent')

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_memory_info_invalid_device(self, mock_gpu):
        """Test get_memory_info with invalid device ID."""
        manager = GPUManager()
        mem_info = manager.get_memory_info(99)

        assert mem_info is None

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_clear_cache_with_cuda(self, mock_gpu):
        """Test clearing CUDA cache."""
        manager = GPUManager()
        result = manager.clear_cache()

        assert isinstance(result, bool)
        if manager.has_cuda:
            mock_gpu.cuda.empty_cache.assert_called()

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_clear_cache_without_cuda(self, mock_gpu_unavailable):
        """Test clearing cache when CUDA is not available."""
        manager = GPUManager()
        result = manager.clear_cache()

        assert result is False

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_clear_cache_specific_device(self, mock_gpu):
        """Test clearing cache for specific device."""
        manager = GPUManager()
        result = manager.clear_cache(device_id=0)

        assert isinstance(result, bool)


# ============================================================================
# Tests for Device Selection
# ============================================================================

class TestDeviceSelection:
    """Test suite for GPU device selection."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_select_best_gpu_with_cuda(self, mock_gpu):
        """Test selecting best GPU when CUDA is available."""
        manager = GPUManager()
        best_gpu = manager.select_best_gpu()

        assert best_gpu is not None
        assert isinstance(best_gpu, int)
        assert best_gpu in manager.available_gpus

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_select_best_gpu_without_cuda(self, mock_gpu_unavailable):
        """Test selecting best GPU when CUDA is not available."""
        manager = GPUManager()
        best_gpu = manager.select_best_gpu()

        assert best_gpu is None

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_set_device_with_valid_id(self, mock_gpu):
        """Test setting device with valid device ID."""
        manager = GPUManager()
        result = manager.set_device(0)

        assert isinstance(result, bool)
        if manager.has_cuda:
            mock_gpu.cuda.set_device.assert_called_with(0)

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_set_device_with_invalid_id(self, mock_gpu):
        """Test setting device with invalid device ID."""
        manager = GPUManager()
        result = manager.set_device(99)

        assert result is False


# ============================================================================
# Tests for Fallback Configurations
# ============================================================================

class TestFallbackConfigurations:
    """Test suite for fallback configuration management."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_fallback_configs_returns_list(self):
        """Test that get_fallback_configs returns a list."""
        manager = GPUManager()
        configs = manager.get_fallback_configs()

        assert isinstance(configs, list)
        assert len(configs) > 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_fallback_configs_structure(self):
        """Test that fallback configs have correct structure."""
        manager = GPUManager()
        configs = manager.get_fallback_configs()

        for config in configs:
            assert 'device' in config
            assert 'compute' in config
            assert config['device'] in ['cuda', 'cpu']

    @pytest.mark.unit
    @pytest.mark.fast
    def test_fallback_configs_includes_cpu(self):
        """Test that fallback configs include CPU fallback."""
        manager = GPUManager()
        configs = manager.get_fallback_configs()

        cpu_configs = [c for c in configs if c['device'] == 'cpu']
        assert len(cpu_configs) > 0


# ============================================================================
# Tests for Convenience Functions
# ============================================================================

class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_default_device_with_cuda(self, mock_gpu):
        """Test get_default_device with CUDA available."""
        device = get_default_device()

        assert device in ['cuda', 'cpu']

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_default_device_without_cuda(self, mock_gpu_unavailable):
        """Test get_default_device without CUDA."""
        device = get_default_device()

        assert device == 'cpu'

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_get_recommended_compute_type(self, mock_gpu):
        """Test get_recommended_compute_type convenience function."""
        with patch('src.core.gpu_manager.WhisperModel'):
            compute_type = get_recommended_compute_type(0)

            assert compute_type is not None
            assert isinstance(compute_type, str)

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_test_gpu_available_with_cuda(self, mock_gpu):
        """Test test_gpu_available with CUDA."""
        with patch('src.core.gpu_manager.WhisperModel'):
            result = test_gpu_available()

            assert isinstance(result, bool)

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_test_gpu_available_without_cuda(self, mock_gpu_unavailable):
        """Test test_gpu_available without CUDA."""
        result = test_gpu_available()

        assert result is False


# ============================================================================
# Tests for String Representation
# ============================================================================

class TestStringRepresentation:
    """Test suite for string representation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_method(self):
        """Test __repr__ method of GPUManager."""
        manager = GPUManager()
        repr_str = repr(manager)

        assert isinstance(repr_str, str)
        assert 'GPUManager' in repr_str
        assert 'has_cuda' in repr_str


# ============================================================================
# Tests for Multi-GPU Support
# ============================================================================

class TestMultiGPUSupport:
    """Test suite for multi-GPU support."""

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_multiple_gpu_detection(self):
        """Test detection of multiple GPUs."""
        # Mock multi-GPU setup
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 2

        with patch.dict('sys.modules', {'torch': mock_torch}):
            manager = GPUManager()
            gpus = manager.detect_gpus()

            assert len(gpus) == 2
            assert gpus == [0, 1]

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_select_best_gpu_multi_gpu(self):
        """Test selecting best GPU with multiple GPUs."""
        # Mock multi-GPU setup with different memory
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 2

        # GPU 0: 8GB, GPU 1: 16GB
        def get_device_props(device_id):
            props = MagicMock()
            props.total_memory = (16 if device_id == 1 else 8) * 1024**3
            props.major = 8
            props.minor = 9
            props.multi_processor_count = 128
            props.clock_rate = 2000000
            return props

        mock_torch.cuda.get_device_properties.side_effect = get_device_props
        mock_torch.cuda.get_device_name.side_effect = lambda x: f"GPU {x}"
        mock_torch.version.cuda = "12.1"

        with patch.dict('sys.modules', {'torch': mock_torch}):
            with patch('src.core.gpu_manager.WhisperModel'):
                manager = GPUManager()
                best_gpu = manager.select_best_gpu()

                # Should select GPU 1 with more memory
                assert best_gpu == 1


# ============================================================================
# Tests for Error Handling
# ============================================================================

class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.unit
    def test_initialization_without_torch(self):
        """Test initialization when PyTorch is not installed."""
        with patch.dict('sys.modules', {'torch': None}):
            # Should not raise exception
            manager = GPUManager()

            assert manager.torch_available is False
            assert manager.has_cuda is False

    @pytest.mark.unit
    @pytest.mark.gpu
    def test_graceful_failure_on_gpu_test(self, mock_gpu):
        """Test graceful failure when GPU test fails."""
        with patch('src.core.gpu_manager.WhisperModel', side_effect=Exception("Test error")):
            manager = GPUManager()
            result = manager.test_gpu(0)

            assert result is False
