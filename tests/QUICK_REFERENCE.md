# Testing Quick Reference Card

## Installation

```bash
pip install -r requirements-dev.txt
```

## Common Commands

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html --cov-report=term
```

### Run Specific Test Types
```bash
pytest -m fast              # Fast tests only
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Skip slow tests
pytest -m "not gpu"         # Skip GPU tests
```

### Run Specific Files
```bash
pytest tests/unit/test_transcription.py
pytest tests/unit/test_database.py
pytest tests/integration/test_workflow.py
```

### Run Specific Tests
```bash
pytest tests/unit/test_transcription.py::TestTimestampFormatting
pytest -k "timestamp"       # Tests matching pattern
```

### Parallel Execution
```bash
pytest -n auto              # Auto-detect CPUs
pytest -n 4                 # Use 4 workers
```

### Verbose Output
```bash
pytest -v                   # Verbose
pytest -vv                  # Very verbose
pytest -s                   # Show print statements
```

## Using the Helper Script

### Basic Usage
```bash
python run_tests.py                    # All tests
python run_tests.py --fast             # Fast tests
python run_tests.py --unit             # Unit tests
python run_tests.py --coverage         # With coverage
python run_tests.py --parallel         # Parallel
```

### Advanced Usage
```bash
python run_tests.py --fast --coverage  # Fast tests with coverage
python run_tests.py --unit --verbose   # Unit tests, verbose
python run_tests.py --file tests/unit/test_transcription.py
python run_tests.py --pattern timestamp
python run_tests.py --list             # List all tests
```

## Available Fixtures

### Most Used Fixtures
- `sample_audio_file` - Test audio (auto-generated)
- `temp_dir` - Temporary directory
- `temp_db` - Temporary database
- `mock_gpu` - Mocked GPU
- `mock_whisper_model` - Mocked Whisper
- `transcription_engine` - Complete setup

### Usage Example
```python
def test_example(sample_audio_file, temp_dir):
    result = process_audio(sample_audio_file, temp_dir)
    assert result is not None
```

## Test Markers

### Marking Tests
```python
@pytest.mark.fast
@pytest.mark.unit
def test_something():
    pass
```

### Available Markers
- `fast` - Fast tests (< 1 second)
- `slow` - Slow tests (> 1 second)
- `unit` - Unit tests
- `integration` - Integration tests
- `gpu` - Requires GPU
- `requires_ffmpeg` - Requires ffmpeg
- `requires_audio` - Requires audio files

## Test Statistics

- **Total Tests:** 91
- **Test Classes:** 23
- **Test Files:** 3
- **Fixtures:** 15+

## Coverage

### View Coverage Report
```bash
# Generate and open HTML report
pytest --cov=. --cov-report=html
start htmlcov/index.html
```

### Coverage Goals
- Minimum: 70% (enforced)
- Target: 80-90%
- Critical: 95%+

## Directory Structure

```
tests/
├── conftest.py              # Fixtures
├── unit/
│   ├── test_transcription.py  # 40+ tests
│   └── test_database.py       # 35+ tests
└── integration/
    └── test_workflow.py       # 16+ tests
```

## Troubleshooting

### Import Errors
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```

### Tests Too Slow
```bash
pytest -m fast                 # Only fast tests
pytest -n auto                 # Parallel execution
```

### Coverage Issues
```bash
pytest --cache-clear --cov=.   # Clear cache
```

## Documentation

- **Full Guide:** `tests/README.md`
- **Fixtures Guide:** `tests/fixtures/README.md`
- **Implementation Report:** `TESTING_FRAMEWORK_REPORT.md`

## Help

```bash
pytest --help                  # Pytest help
pytest --markers               # List all markers
pytest --fixtures              # List all fixtures
python run_tests.py --help     # Helper script help
```

---

**Quick Tip:** Use `python run_tests.py --coverage` for the easiest way to run tests with coverage!
