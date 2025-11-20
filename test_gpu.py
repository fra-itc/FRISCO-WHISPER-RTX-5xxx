"""
Quick GPU Test Script for RTX 5080 Compatibility
Tests PyTorch CUDA availability and compute capability
"""

import torch
import sys

def test_gpu():
    """Test GPU availability and capabilities"""

    print("=" * 60)
    print("GPU COMPATIBILITY TEST")
    print("=" * 60)

    # Check PyTorch version
    print(f"\nPyTorch Version: {torch.__version__}")
    print(f"CUDA Version (PyTorch): {torch.version.cuda}")

    # Check CUDA availability
    cuda_available = torch.cuda.is_available()
    print(f"\nCUDA Available: {cuda_available}")

    if not cuda_available:
        print("\n[ERROR] CUDA is not available!")
        print("   This means PyTorch cannot access the GPU.")
        print("\n   Possible causes:")
        print("   - PyTorch not installed with CUDA support")
        print("   - NVIDIA drivers not installed or outdated")
        print("   - GPU not detected by system")
        print("\n   Solution: Follow PYTORCH_RTX5080_UPGRADE_GUIDE.md")
        sys.exit(1)

    # GPU Details
    print(f"\nGPU Name: {torch.cuda.get_device_name(0)}")

    # Compute Capability
    capability = torch.cuda.get_device_capability(0)
    print(f"Compute Capability: sm_{capability[0]}{capability[1]} ({capability[0]}.{capability[1]})")

    # Memory
    props = torch.cuda.get_device_properties(0)
    total_memory_gb = props.total_memory / 1e9
    print(f"Total Memory: {total_memory_gb:.2f} GB")
    print(f"Multiprocessors: {props.multi_processor_count}")

    # Check if RTX 5080 is properly supported
    if capability == (12, 0):
        print("\n[SUCCESS] RTX 5080 (sm_120) is properly supported!")
        print("   Your PyTorch installation is compatible with RTX 5080.")
    elif capability[0] < 12:
        print(f"\n[WARNING] Compute capability {capability} detected")
        print("   This is not an RTX 5080, or PyTorch doesn't fully support it.")

    # Test GPU operation
    print("\nTesting GPU Tensor Operation...")
    try:
        x = torch.randn(1000, 1000).cuda()
        y = torch.randn(1000, 1000).cuda()
        z = torch.matmul(x, y)
        print("[OK] GPU Tensor Operation: Success")
    except Exception as e:
        print(f"[ERROR] GPU Tensor Operation Failed: {e}")
        sys.exit(1)

    # Check for compatibility warnings
    print("\nCompatibility Check:")
    if capability == (12, 0) and torch.__version__.startswith("2.5"):
        print("[OK] PyTorch 2.5+ with sm_120 support detected")
    elif capability == (12, 0):
        print("[WARNING] PyTorch version may not fully support sm_120")
        print(f"   Current version: {torch.__version__}")
        print("   Recommended: PyTorch 2.5.1+")

    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)

    return True

if __name__ == "__main__":
    try:
        test_gpu()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)
