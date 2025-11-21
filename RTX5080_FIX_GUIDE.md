# RTX 5080 Compatibility Fix Guide

## Issues Found

1. **PyTorch Incompatibility**: Your PyTorch 2.9.1+cu126 doesn't support RTX 5080's sm_120 (CUDA capability 12.0)
2. **Web Server Bug**: Fixed undefined `transcription_engine` in web_server.py:270

## Solutions (Choose One)

### Option 1: Custom PyTorch Build for RTX 5080 (RECOMMENDED)

This uses a community-built PyTorch with sm_120 support.

#### Requirements:
- Python 3.10 or 3.11 (check with `python --version`)

#### Steps:

1. **Backup current environment:**
```powershell
pip freeze > backup_requirements.txt
```

2. **Download custom PyTorch:**
```powershell
# Clone the repository with custom build
git clone https://github.com/kentstone84/pytorch-rtx5080-support.git
cd pytorch-rtx5080-support

# Run the automated installer
.\install.ps1
```

3. **Or Manual Installation:**
```powershell
# Download the release files from GitHub
# https://github.com/kentstone84/pytorch-rtx5080-support/releases

# Recombine split archive
cat pytorch-2.10.0a0-sm120-windows.tar.gz.part* > pytorch-2.10.0a0-sm120-windows.tar.gz

# Extract
tar -xzf pytorch-2.10.0a0-sm120-windows.tar.gz

# Copy torch folder to your Python site-packages
# Location: C:\Python311\Lib\site-packages\torch\
```

4. **Verify:**
```python
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Architectures: {torch.cuda.get_arch_list()}")  # Should show sm_120
```

### Option 2: PyTorch Nightly Build (EXPERIMENTAL)

PyTorch nightly may have partial sm_120 support:

```powershell
# Uninstall current PyTorch
pip uninstall torch torchvision torchaudio -y

# Install nightly with CUDA 12.8
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
```

**Note:** Windows nightly builds may not have full sm_120 support yet.

### Option 3: Use CPU Mode (SLOW but WORKS)

If GPU fix is too complex, use CPU mode temporarily:

```python
# Edit whisper_transcribe_frisco.py
# Change line ~118 to force CPU:
device = "cpu"
compute_type = "int8"
```

### Option 4: Force Compatibility (NOT RECOMMENDED)

PyTorch may work despite warnings using backward compatibility:

```python
import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['TORCH_CUDA_ARCH_LIST'] = '9.0+PTX'  # Use sm_90 compatibility
```

Add this to the top of your scripts before importing torch.

## After Installing PyTorch Fix

### Test Your Setup:

1. **Test GPU:**
```powershell
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

2. **Test CLI:**
```powershell
python whisper_transcribe_frisco.py
```
   - Should show the menu now without crashing

3. **Test Web UI:**
```powershell
python src/ui/web_server.py
```
   - Navigate to http://localhost:8000
   - Should load without errors

## Verification Checklist

- [ ] PyTorch imports without warnings
- [ ] `torch.cuda.is_available()` returns `True`
- [ ] `torch.cuda.get_arch_list()` includes `sm_120`
- [ ] CLI menu displays correctly
- [ ] Web UI loads at http://localhost:8000
- [ ] Test transcription completes successfully

## Troubleshooting

### "Module 'torch' has no attribute 'cuda'"
- PyTorch CPU version installed instead of GPU
- Reinstall with CUDA support

### "CUDA out of memory"
- Reduce model size: use 'medium' instead of 'large-v3'
- Close other GPU applications

### Web UI still not loading
- Check if port 8000 is already in use
- Try: `python src/ui/web_server.py --port 8001`

### CLI still crashes
- Check Python version (needs 3.10 or 3.11)
- Verify all dependencies: `pip install -r requirements.txt`

## Need Help?

1. Check PyTorch installation: `pip show torch`
2. Check CUDA version: `nvidia-smi`
3. Review logs in `logs/` directory
4. Open issue on GitHub with error details

## What Was Fixed

### Web Server Bug (src/ui/web_server.py:270-271)
**Before:**
```python
compute_type=transcription_engine.compute_type,  # ❌ undefined variable
device=transcription_engine.device,
```

**After:**
```python
compute_type = transcription_service.engine.compute_type  # ✅ correct reference
device = transcription_service.engine.device
```

This fix allows the web UI to create transcription jobs without crashing.
