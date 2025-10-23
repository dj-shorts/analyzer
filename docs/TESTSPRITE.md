# TestSprite Integration Guide

Complete guide for integrating TestSprite test reporting platform with DJ Shorts Analyzer test suite.

## 🎯 Overview

TestSprite provides:
- **Rich Test Reporting**: Screenshots, videos, logs
- **Historical Tracking**: Test trends over time
- **Flaky Test Detection**: Automatic identification
- **Team Collaboration**: Shared test results
- **Analytics**: Test suite health metrics

## 📊 Current Test Suite

We have **~200 tests** across multiple suites:

| Test Suite | Tests | Description |
|------------|-------|-------------|
| `test_analyzer.py` | ~10 | Core analyzer functionality |
| `test_beats.py` | ~15 | Beat detection algorithms |
| `test_cancellation_e3.py` | ~30 | Signal handling & cleanup |
| `test_integration_f2.py` | ~80 | End-to-end workflows |
| `test_json_schema_e1.py` | ~20 | Schema validation |
| `test_motion_epic_c.py` | ~15 | Motion analysis |
| `test_performance_f3.py` | ~20 | Performance benchmarks |
| `test_progress_events_e2.py` | ~25 | Progress tracking |
| `test_prometheus_metrics_g1.py` | ~30 | Metrics collection |
| `test_setup.py` | ~10 | Setup scripts |

## 🚀 Quick Start

### Prerequisites

1. **TestSprite Account**
   - Sign up at https://testsprite.com
   - Create project "dj-shorts-analyzer"
   - Get API key from Settings

2. **Install TestSprite SDK**
   ```bash
   uv add testsprite
   ```

### Configuration

#### 1. Environment Variables

```bash
# .env
TESTSPRITE_API_KEY=your_api_key_here
TESTSPRITE_PROJECT_ID=dj-shorts-analyzer
TESTSPRITE_ENABLED=true
TESTSPRITE_UPLOAD_ARTIFACTS=true
```

#### 2. pytest Configuration

Create or update `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# TestSprite configuration
testsprite_enabled = true
testsprite_project = dj-shorts-analyzer
testsprite_upload_screenshots = true
testsprite_upload_videos = true
testsprite_upload_logs = true
```

#### 3. conftest.py Setup

Add TestSprite hooks to `tests/conftest.py`:

```python
import pytest
import os
from pathlib import Path

# TestSprite integration (when available)
TESTSPRITE_ENABLED = os.getenv("TESTSPRITE_ENABLED", "false").lower() == "true"

if TESTSPRITE_ENABLED:
    try:
        from testsprite import TestSprite
        
        testsprite = TestSprite(
            api_key=os.getenv("TESTSPRITE_API_KEY"),
            project=os.getenv("TESTSPRITE_PROJECT_ID", "dj-shorts-analyzer"),
        )
        
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(item, call):
            outcome = yield
            report = outcome.get_result()
            
            if report.when == "call":
                testsprite.report_test(
                    name=item.nodeid,
                    status=report.outcome,
                    duration=report.duration,
                    error=str(report.longrepr) if report.failed else None,
                )
    except ImportError:
        print("TestSprite SDK not installed. Install with: uv add testsprite")
```

## 📝 Test Metadata

### Adding Tags

```python
import pytest

@pytest.mark.testsprite(
    tags=["audio", "critical"],
    priority="high",
    requirements=["REQ-001", "REQ-002"],
)
def test_audio_extraction():
    """Test audio extraction from video file."""
    pass
```

### Test Categories

```python
# Category markers
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.regression

def test_something():
    pass
```

## 📸 Artifact Attachment

### Screenshots

```python
def test_video_frame_extraction(tmp_path):
    # Extract frame
    frame_path = tmp_path / "frame.png"
    extract_frame(video_path, frame_path)
    
    # Attach to TestSprite
    if TESTSPRITE_ENABLED:
        testsprite.attach_screenshot(frame_path)
```

### Video Files

```python
def test_video_export(tmp_path):
    # Export video
    output_path = tmp_path / "clip.mp4"
    export_clip(input_video, output_path)
    
    # Attach to TestSprite
    if TESTSPRITE_ENABLED:
        testsprite.attach_video(output_path)
```

### Logs and Metrics

```python
def test_performance_metrics(tmp_path):
    # Generate metrics
    metrics_path = tmp_path / "metrics.json"
    run_analysis(video_path, metrics_path)
    
    # Attach to TestSprite
    if TESTSPRITE_ENABLED:
        testsprite.attach_file(metrics_path, "metrics")
```

## 🔄 CI Integration

### GitHub Actions

```yaml
name: Tests with TestSprite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      
      - name: Run tests with TestSprite
        env:
          TESTSPRITE_API_KEY: ${{ secrets.TESTSPRITE_API_KEY }}
          TESTSPRITE_ENABLED: true
        run: |
          uv run pytest -v --tb=short
      
      - name: Upload TestSprite Report
        if: always()
        uses: testsprite/upload-action@v1
        with:
          api-key: ${{ secrets.TESTSPRITE_API_KEY }}
          project: dj-shorts-analyzer
          results-path: ./test-results/
```

## 📊 Dashboard Setup

### Test Suites Organization

Organize tests in TestSprite dashboard:

1. **Unit Tests**
   - Fast, isolated tests
   - < 1s execution time
   - Run on every commit

2. **Integration Tests**
   - End-to-end workflows
   - Use real video files
   - Run on PR

3. **Performance Tests**
   - Benchmark validation
   - Track regression
   - Run daily

4. **Regression Tests**
   - Known issues prevention
   - Run before release

### Custom Views

Create views for:
- **Failed Tests**: All failures in last 7 days
- **Flaky Tests**: Tests with <80% stability
- **Slow Tests**: Tests taking >10s
- **Critical Tests**: High priority tests

## 📈 Metrics and Analytics

### Test Suite Health

Key metrics to track:
- **Pass Rate**: % of passing tests
- **Flakiness**: % of flaky tests
- **Duration**: Average test execution time
- **Coverage**: Code coverage percentage

### Performance Trends

Track over time:
- Processing time per video
- Memory usage during tests
- Clip generation success rate
- Export quality metrics

### Flaky Test Detection

TestSprite automatically detects:
- Tests that pass/fail intermittently
- Tests affected by timing issues
- Tests with race conditions

## 🐛 Troubleshooting

### TestSprite SDK Not Found

```bash
# Install SDK
uv add testsprite

# Verify installation
python -c "import testsprite; print(testsprite.__version__)"
```

### API Key Issues

```bash
# Test API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.testsprite.com/v1/projects
```

### Upload Failures

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# TestSprite will show detailed upload logs
```

### Missing Artifacts

```python
# Verify file exists before attach
if Path(artifact_path).exists():
    testsprite.attach_file(artifact_path)
else:
    pytest.fail(f"Artifact not found: {artifact_path}")
```

## 🔐 Security

### Protect API Keys

```bash
# Never commit API keys
echo "TESTSPRITE_API_KEY=*" >> .gitignore

# Use GitHub Secrets
gh secret set TESTSPRITE_API_KEY
```

### Access Control

- Limit API key permissions to test results
- Use separate keys for CI and local dev
- Rotate keys every 90 days

## 📚 Best Practices

### 1. Organize Tests

```python
# Use clear test names
def test_video_export_creates_clip_with_correct_duration():
    pass  # Descriptive name

# Add docstrings
def test_audio_extraction():
    """
    Verify audio extraction produces valid audio file.
    
    Given: A video file with audio track
    When: Audio extraction is performed
    Then: Output file exists and contains audio data
    """
    pass
```

### 2. Clean Up Artifacts

```python
@pytest.fixture
def video_file(tmp_path):
    """Create temporary video file."""
    video = tmp_path / "test.mp4"
    # Create video
    yield video
    # Cleanup automatic with tmp_path
```

### 3. Tag Appropriately

```python
@pytest.mark.slow  # Tests > 5s
@pytest.mark.requires_ffmpeg  # System dependency
@pytest.mark.integration  # Integration test
def test_full_analysis_pipeline():
    pass
```

## 🔄 Migration from Current Setup

Current setup → TestSprite:

1. **Keep existing tests unchanged**
   - TestSprite wraps pytest
   - No test modifications needed

2. **Add TestSprite config**
   - Environment variables
   - pytest.ini settings
   - conftest.py hooks

3. **Gradual rollout**
   - Enable for CI first
   - Add to local dev later
   - Migrate one suite at a time

## 📞 Support

- **Documentation**: https://docs.testsprite.com
- **API Reference**: https://docs.testsprite.com/api
- **pytest Integration**: https://docs.testsprite.com/pytest
- **Support Email**: support@testsprite.com

## 🔗 Related Documentation

- [CI/CD Pipeline](./CI_CD.md) - GitHub Actions integration
- [Setup Guide](./SETUP.md) - Development environment
- [Testing Guide](../tests/README.md) - Running tests locally

## 📊 Status

**Implementation Status**: Ready for integration

**Prerequisites**:
- ✅ Test suite organized (~200 tests)
- ✅ pytest configured
- ✅ CI/CD pipeline ready
- ⏳ TestSprite account setup required
- ⏳ API key configuration needed

**Next Steps**:
1. Create TestSprite account
2. Get API key
3. Add to CI secrets
4. Test integration locally
5. Enable in CI/CD
6. Configure dashboard


