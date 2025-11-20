# PyTorch Upgrade Guide for RTX 5080

## Issue
NVIDIA GeForce RTX 5080 with CUDA capability **sm_120** is not compatible with PyTorch 2.1.0, which only supports up to **sm_90**.

## Solution
Upgrade to PyTorch 2.5.1+ with CUDA 12.4+ support.

---

## Installation Instructions

### Prerequisites
- **NVIDIA Driver**: Version 560+ (supports CUDA 12.6)
- **Python**: 3.10 or 3.11
- **CUDA Toolkit**: 12.4 or 12.6 (optional, PyTorch wheels include CUDA runtime)

### Option A: Stable Release (Recommended)

#### 1. Uninstall Old PyTorch
```bash
pip uninstall torch torchvision torchaudio -y
```

#### 2. Install PyTorch 2.5.1 with CUDA 12.4
```bash
pip install torch>=2.5.1 torchvision>=0.20.1 torchaudio>=2.5.1 --index-url https://download.pytorch.org/whl/cu124
```

#### 3. Install Other Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Verify Installation
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}'); print(f'Compute Capability: {torch.cuda.get_device_capability(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Expected output:
```
PyTorch: 2.5.1+cu124
CUDA Available: True
GPU: NVIDIA GeForce RTX 5080
Compute Capability: (12, 0)
```

---

### Option B: Nightly Build (Maximum Compatibility)

#### 1. Uninstall Old PyTorch
```bash
pip uninstall torch torchvision torchaudio -y
```

#### 2. Install PyTorch Nightly with CUDA 12.6
```bash
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu126
```

#### 3. Install Other Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Verify Installation
```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}'); print(f'Compute Capability: {torch.cuda.get_device_capability(0) if torch.cuda.is_available() else \"N/A\"}')"
```

---

## Docker Installation

### 1. Rebuild Docker Image
```bash
docker-compose build --no-cache
```

### 2. Run Container
```bash
docker-compose up -d
```

### 3. Verify GPU Access
```bash
docker exec -it frisco-whisper python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

---

## Testing

### Quick GPU Test
```python
import torch

# Check CUDA availability
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"CUDA Version: {torch.version.cuda}")
print(f"PyTorch Version: {torch.__version__}")

# Check GPU details
if torch.cuda.is_available():
    print(f"\nGPU Name: {torch.cuda.get_device_name(0)}")
    print(f"Compute Capability: {torch.cuda.get_device_capability(0)}")
    print(f"Total Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    # Test tensor operation on GPU
    x = torch.randn(1000, 1000).cuda()
    y = torch.randn(1000, 1000).cuda()
    z = torch.matmul(x, y)
    print(f"\nGPU Tensor Operation: Success ✓")
else:
    print("\n❌ CUDA not available!")
```

Save as `test_gpu.py` and run:
```bash
python test_gpu.py
```

### Whisper Transcription Test
```bash
python whisper_transcribe_frisco.py
```

Select a test audio file and verify:
- ✅ Transcription runs on GPU (not CPU)
- ✅ No CUDA compatibility warnings
- ✅ Expected performance (~8-10s for 1 min audio on RTX 5080)

---

## Troubleshooting

### Issue: "CUDA not available"

**Check 1: NVIDIA Driver**
```bash
nvidia-smi
```
Should show RTX 5080 and Driver Version 560+

**Check 2: CUDA Runtime**
```bash
python -c "import torch; print(torch.version.cuda)"
```
Should show 12.4 or 12.6

**Check 3: PyTorch CUDA Build**
```bash
python -c "import torch; print(torch.__version__)"
```
Should include `+cu124` or `+cu126`

### Issue: "sm_120 not compatible" Warning Persists

This means PyTorch version is still old. Verify:
```bash
pip show torch
```

Reinstall with correct index URL:
```bash
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### Issue: "faster-whisper" Compatibility Error

Update faster-whisper:
```bash
pip install --upgrade faster-whisper
```

### Issue: Docker Container GPU Access Failed

**Check 1: NVIDIA Container Toolkit**
```bash
nvidia-ctk --version
```

**Check 2: Docker Runtime**
```bash
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
```

**Check 3: Rebuild with No Cache**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Performance Expectations

### RTX 5080 with PyTorch 2.5.1+ (CUDA 12.4+)

| Audio Length | Model Size | Compute Type | Expected Time |
|--------------|------------|--------------|---------------|
| 1 minute     | large-v3   | float16      | ~8-10s        |
| 5 minutes    | large-v3   | float16      | ~40-50s       |
| 10 minutes   | large-v3   | float16      | ~80-100s      |
| 1 minute     | large-v3   | int8         | ~5-7s         |

### Before Upgrade (CPU Fallback)
- Same workload: **10-20x slower**
- Uses CPU instead of RTX 5080

---

## Verification Checklist

After upgrade, verify:
- [ ] `torch.cuda.is_available()` returns `True`
- [ ] `torch.cuda.get_device_capability(0)` returns `(12, 0)`
- [ ] GPU name shows "NVIDIA GeForce RTX 5080"
- [ ] No CUDA compatibility warnings during import
- [ ] Whisper transcription runs on GPU
- [ ] Performance matches expectations (~8-10s per minute)
- [ ] Docker container (if used) builds successfully
- [ ] All existing tests pass: `pytest tests/`

---

## Version Compatibility Matrix

| Component        | Minimum | Recommended | Nightly    |
|------------------|---------|-------------|------------|
| PyTorch          | 2.5.0   | 2.5.1       | 2.6.0-dev  |
| CUDA Toolkit     | 12.4    | 12.4        | 12.6       |
| TorchVision      | 0.20.0  | 0.20.1      | latest     |
| TorchAudio       | 2.5.0   | 2.5.1       | latest     |
| Python           | 3.10    | 3.11        | 3.11       |
| NVIDIA Driver    | 555+    | 560+        | 565+       |
| faster-whisper   | 1.0.0   | 1.0.3+      | latest     |

---

## References

- [PyTorch Official Installation](https://pytorch.org/get-started/locally/)
- [NVIDIA CUDA Compute Capability](https://developer.nvidia.com/cuda-gpus)
- [RTX 50 Series Specifications](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/)
- [PyTorch Release Notes](https://github.com/pytorch/pytorch/releases)

---

## Support

For issues specific to this project:
- Check `docs/` folder for architecture documentation
- Review `TESTING_FRAMEWORK_REPORT.md` for test results
- See `WEB_UI_INTEGRATION_REPORT.md` for known issues

For PyTorch issues:
- [PyTorch Forums](https://discuss.pytorch.org/)
- [PyTorch GitHub Issues](https://github.com/pytorch/pytorch/issues)
