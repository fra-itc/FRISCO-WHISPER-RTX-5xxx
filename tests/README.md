# Testing Framework - Frisco Whisper RTX

Comprehensive pytest-based testing framework for the Whisper RTX transcription application.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Available Fixtures](#available-fixtures)
- [Test Categories](#test-categories)
- [Coverage Reports](#coverage-reports)
- [Writing New Tests](#writing-new-tests)
- [Continuous Integration](#continuous-integration)

## Quick Start

### Installation

1. Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

2. Verify installation:

```bash
pytest --version
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run with detailed output
pytest -vv
```

## Test Structure

```
tests/
├── __init__.py                    # Tests package initialization
├── conftest.py                    # Pytest fixtures and configuration
├── pytest.ini                     # Pytest configuration (in root)
├── README.md                      # This file
├── fixtures/                      # Test data and fixtures
│   ├── README.md                  # Fixtures documentation
│   └── sample_audio.wav          # Auto-generated test audio
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_transcription.py     # Transcription function tests
│   └── test_database.py          # Database operation tests
└── integration/                   # Integration tests
    ├── __init__.py
    └── test_workflow.py          # End-to-end workflow tests
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_transcription.py

# Run specific test class
pytest tests/unit/test_transcription.py::TestTimestampFormatting

# Run specific test function
pytest tests/unit/test_transcription.py::TestTimestampFormatting::test_format_timestamp_zero_seconds

# Run tests matching pattern
pytest -k "timestamp"
```

### Test Categories

#### By Speed

```bash
# Run only fast tests (< 1 second)
pytest -m fast

# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"
```

#### By Type

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run GPU-related tests
pytest -m gpu
```

#### By Requirements

```bash
# Skip tests requiring GPU
pytest -m "not gpu"

# Skip tests requiring ffmpeg
pytest -m "not requires_ffmpeg"

# Skip tests requiring audio files
pytest -m "not requires_audio"
```

### Parallel Execution

```bash
# Run tests in parallel (4 workers)
pytest -n 4

# Run tests in parallel (auto-detect CPU count)
pytest -n auto
```

### Verbose Output

```bash
# Show test names and status
pytest -v

# Show all details
pytest -vv

# Show print statements
pytest -s

# Show local variables on failure
pytest -l
```

## Available Fixtures

### Session-scoped Fixtures

These are created once per test session:

#### `test_data_dir`
- **Type**: Path
- **Description**: Path to the test fixtures directory
- **Usage**:
```python
def test_example(test_data_dir):
    assert test_data_dir.exists()
```

#### `sample_audio_file`
- **Type**: Path
- **Description**: 1-second silent WAV file (16kHz mono)
- **Auto-generated**: Yes
- **Usage**:
```python
def test_audio(sample_audio_file):
    assert sample_audio_file.exists()
    assert sample_audio_file.suffix == '.wav'
```

#### `sample_m4a_file`
- **Type**: Path
- **Description**: Path to M4A test file (if available)
- **Auto-generated**: No
- **Usage**:
```python
def test_m4a_conversion(sample_m4a_file):
    if sample_m4a_file.exists():
        # Test M4A conversion
        pass
```

### Function-scoped Fixtures

These are created for each test function:

#### `temp_dir`
- **Type**: Path
- **Description**: Temporary directory for test outputs
- **Cleanup**: Automatic
- **Usage**:
```python
def test_output(temp_dir):
    output_file = temp_dir / "test.txt"
    output_file.write_text("test")
    # Directory automatically cleaned up after test
```

#### `temp_db`
- **Type**: Path
- **Description**: Temporary SQLite database with transcriptions table
- **Cleanup**: Automatic
- **Usage**:
```python
def test_database(temp_db):
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transcriptions")
    conn.close()
```

#### `mock_gpu`
- **Type**: Mock
- **Description**: Mocked torch module with CUDA enabled
- **Usage**:
```python
def test_gpu_function(mock_gpu):
    # GPU functions will use the mock
    result = some_gpu_function()
    mock_gpu.cuda.is_available.assert_called()
```

#### `mock_gpu_unavailable`
- **Type**: Mock
- **Description**: Mocked torch module with CUDA disabled
- **Usage**:
```python
def test_cpu_fallback(mock_gpu_unavailable):
    # Test CPU fallback when GPU unavailable
    result = some_function_with_fallback()
```

#### `mock_whisper_model`
- **Type**: Mock
- **Description**: Mocked WhisperModel for testing
- **Returns**: Fake transcription segments
- **Usage**:
```python
def test_transcription(mock_whisper_model):
    segments, info = mock_whisper_model.transcribe("audio.wav")
    assert len(segments) > 0
```

#### `transcription_engine`
- **Type**: dict
- **Description**: Initialized transcription engine with mocks
- **Contents**: model, gpu, device, compute_type
- **Usage**:
```python
def test_engine(transcription_engine):
    model = transcription_engine['model']
    device = transcription_engine['device']
    assert device == 'cuda'
```

#### `mock_ffmpeg`
- **Type**: dict
- **Description**: Mocked ffmpeg subprocess calls
- **Contents**: run, popen, check_call
- **Usage**:
```python
def test_conversion(mock_ffmpeg):
    convert_audio("input.m4a", "output.wav")
    mock_ffmpeg['run'].assert_called()
```

#### `sample_transcription_result`
- **Type**: dict
- **Description**: Sample transcription result data
- **Usage**:
```python
def test_result_processing(sample_transcription_result):
    segments = sample_transcription_result['segments']
    assert len(segments) == 2
```

#### `sample_srt_content`
- **Type**: str
- **Description**: Sample SRT subtitle content
- **Usage**:
```python
def test_srt_parsing(sample_srt_content):
    lines = sample_srt_content.split('\n')
    assert '00:00:00,000' in sample_srt_content
```

## Test Categories

### Unit Tests (`tests/unit/`)

#### test_transcription.py

Tests for core transcription functionality:
- ✓ Timestamp formatting (SRT format)
- ✓ GPU detection and testing
- ✓ Audio file conversion
- ✓ Audio duration detection
- ✓ Transcription with different models
- ✓ Color output formatting
- ✓ Dependency checking
- ✓ Model selection

**Example**:
```bash
# Run all transcription unit tests
pytest tests/unit/test_transcription.py -v
```

#### test_database.py

Tests for database operations:
- ✓ Schema creation and validation
- ✓ INSERT operations
- ✓ SELECT operations (with filters)
- ✓ UPDATE operations
- ✓ DELETE operations
- ✓ Complex queries (aggregations, grouping)
- ✓ Data integrity and constraints

**Example**:
```bash
# Run all database unit tests
pytest tests/unit/test_database.py -v
```

### Integration Tests (`tests/integration/`)

#### test_workflow.py

Tests for end-to-end workflows:
- ✓ Complete transcription workflow
- ✓ Auto language detection workflow
- ✓ Translation workflow
- ✓ Batch processing
- ✓ Error handling scenarios
- ✓ Database integration
- ✓ File cleanup
- ✓ Multiple file formats
- ✓ Model selection

**Example**:
```bash
# Run all integration tests
pytest tests/integration/test_workflow.py -v

# Run only fast integration tests
pytest tests/integration/test_workflow.py -m "not slow"
```

## Coverage Reports

### Generate Coverage Reports

```bash
# Run tests with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Open HTML coverage report
# Windows:
start htmlcov/index.html

# Linux/Mac:
open htmlcov/index.html
```

### Coverage Report Locations

- **HTML Report**: `htmlcov/index.html`
- **Terminal Report**: Displayed after test run
- **XML Report**: `coverage.xml` (for CI systems)

### Coverage Goals

- **Minimum Coverage**: 70% (enforced by `--cov-fail-under=70`)
- **Target Coverage**: 80-90%
- **Critical Modules**: 95%+ coverage

### Viewing Coverage

```bash
# Show coverage summary
coverage report

# Show missing lines
coverage report -m

# Generate HTML report
coverage html
```

## Writing New Tests

### Test Structure Template

```python
"""
Description of what this test file covers.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import whisper_transcribe_frisco as wtf


class TestFeatureName:
    """Test suite for feature X."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_basic_functionality(self):
        """Test basic functionality of feature X."""
        result = wtf.some_function()
        assert result is not None

    @pytest.mark.unit
    @pytest.mark.slow
    def test_advanced_functionality(self, sample_audio_file):
        """Test advanced functionality with audio file."""
        result = wtf.process_audio(sample_audio_file)
        assert result == expected_value
```

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use descriptive names: `test_format_timestamp_with_hours`

### Using Markers

```python
# Mark test as slow
@pytest.mark.slow
def test_long_audio():
    pass

# Mark test as requiring GPU
@pytest.mark.gpu
def test_gpu_transcription():
    pass

# Mark test as integration test
@pytest.mark.integration
def test_end_to_end_workflow():
    pass

# Parametrize test with multiple inputs
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiplication(input, expected):
    assert input * 2 == expected
```

### Using Fixtures

```python
def test_with_fixtures(sample_audio_file, temp_dir, mock_gpu):
    """Test using multiple fixtures."""
    # Fixtures are automatically provided
    output_file = temp_dir / "output.srt"

    result = transcribe(sample_audio_file, output_file)

    assert output_file.exists()
    mock_gpu.cuda.is_available.assert_called()
```

### Mocking Examples

```python
from unittest.mock import patch, MagicMock

def test_with_mocking():
    """Test with mocked dependencies."""
    with patch('whisper_transcribe_frisco.WhisperModel') as mock_model:
        mock_model.return_value.transcribe.return_value = ([], None)

        result = wtf.transcribe_audio("test.wav", "output")

        mock_model.assert_called_once()
```

## Continuous Integration

### GitHub Actions

Example `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

Example `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Troubleshooting

### Common Issues

#### Import Errors

If you see import errors:

```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Or use pytest with -p no:cacheprovider
pytest -p no:cacheprovider
```

#### GPU Tests Failing

```bash
# Skip GPU tests if no GPU available
pytest -m "not gpu"
```

#### Slow Test Execution

```bash
# Run only fast tests
pytest -m fast

# Run tests in parallel
pytest -n auto
```

#### Coverage Not Working

```bash
# Reinstall coverage
pip install --upgrade pytest-cov coverage

# Clear cache and rerun
pytest --cache-clear --cov=.
```

## Best Practices

1. **Keep tests fast**: Use mocks for slow operations
2. **Use appropriate markers**: Mark slow, GPU, or integration tests
3. **Clean up resources**: Use fixtures with automatic cleanup
4. **Test edge cases**: Include tests for error conditions
5. **Maintain coverage**: Aim for >80% coverage
6. **Write descriptive names**: Test names should describe what they test
7. **Use parametrize**: Test multiple inputs efficiently
8. **Isolate tests**: Tests should not depend on each other
9. **Mock external dependencies**: Don't rely on external services
10. **Document complex tests**: Add docstrings explaining non-obvious tests

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Mocking in Python](https://docs.python.org/3/library/unittest.mock.html)

## Support

For issues or questions about the testing framework:

1. Check this README
2. Review test examples in `tests/unit/` and `tests/integration/`
3. Check fixture documentation in `tests/conftest.py`
4. Review pytest output with `-vv` flag for detailed information
